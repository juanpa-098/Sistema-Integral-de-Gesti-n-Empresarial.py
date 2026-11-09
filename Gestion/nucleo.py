"""Núcleo de SIGE: errores, permisos, reglas, autenticación, repositorio, reportes y almacén.

Secciones (en orden de dependencia):
    1. Errores            4. Autenticación        7. Almacén (persistencia JSON)
    2. Permisos por rol   5. Repositorio (CRUD)
    3. Reglas de empleados 6. Reportes

Complejidades: Repositorio agregar/actualizar/eliminar/obtener O(n) (búsqueda en lista ligada);
ordenado O(n log n); buscar_id_binaria O(n log n) por el ordenamiento previo + O(log n) la búsqueda.
"""
import json
import os
import re
import unicodedata
from datetime import date

from Gestion.estructuras import ListaLigada, PilaDinamica, ColaDinamica, merge_sort, busqueda_binaria

class ErrorSige(Exception):
    """Base de los errores controlados del sistema."""

class AccesoDenegado(ErrorSige):
    """Autenticación fallida."""

class PermisoInsuficiente(ErrorSige):
    """El rol no puede usar ese módulo o escribir en él."""

class ErrorValidacion(ErrorSige):
    """Datos de un registro inválidos."""


class ErrorNegocio(ErrorSige):
    """Operación imposible por reglas del negocio (sin existencias, etc.)."""

NAV = [("inicio", "Inicio"), ("clientes", "Clientes"), ("productos", "Productos"), ("inventario", "Inventario"),
       ("proveedores", "Proveedores"), ("ventas", "Ventas"), ("compras", "Compras"), ("empleados", "Empleados"),
       ("finanzas", "Finanzas"), ("reportes", "Reportes"), ("admin", "Administración")]
ETIQUETAS = dict(NAV)
ADMIN = "Administrador"

ACC = {
    "Administrador": {"m": [k for k, _ in NAV], "ro": []},
    "Ventas": {"m": ["inicio", "clientes", "productos", "ventas", "reportes"], "ro": ["productos"]},
    "Compras": {"m": ["inicio", "proveedores", "productos", "inventario", "compras"], "ro": ["productos", "inventario"]},
    "Bodega": {"m": ["inicio", "productos", "inventario"], "ro": ["productos"]},
    "Contabilidad": {"m": ["inicio", "finanzas", "reportes"], "ro": []},
    "Recursos Humanos": {"m": ["inicio", "empleados"], "ro": []},
}
ROLES_VALIDOS = tuple(ACC)  # misma lista, un solo lugar donde mantenerla


def puede(rol, modulo):
    return modulo in ACC.get(rol, {"m": ["inicio"]})["m"]


def solo_lectura(rol, modulo):
    return rol != ADMIN and modulo in ACC.get(rol, {}).get("ro", [])


def modulos_de(rol):
    return [(k, ETIQUETAS[k]) for k in ACC.get(rol, {"m": ["inicio"]})["m"]]


def tabla_roles():
    filas = []
    for rol, a in ACC.items():
        mods = [ETIQUETAS[m] + (" (solo lectura)" if m in a["ro"] else "") for m in a["m"] if m != "inicio"]
        filas.append((rol, mods))
    return filas

def validar_cambio_empleado(almacen, usuario, viejo, nuevo):
    es_admin = usuario["rol"] == ADMIN
    if not es_admin and (nuevo["rol"] == ADMIN or (viejo and viejo["rol"] == ADMIN)):
        raise PermisoInsuficiente("Solo un administrador puede gestionar administradores.")
    if viejo and viejo["id"] == usuario["id"]:
        if es_admin and nuevo["rol"] != ADMIN:
            raise PermisoInsuficiente("No puedes quitarte tu propio rol de administrador.")
        if not es_admin and nuevo["rol"] != usuario["rol"]:
            raise PermisoInsuficiente("No puedes cambiar tu propio rol.")


def validar_baja_empleado(almacen, usuario, viejo):
    if usuario["rol"] != ADMIN and viejo["rol"] == ADMIN:
        raise PermisoInsuficiente("Solo un administrador puede gestionar administradores.")
    if viejo["id"] == usuario["id"]:
        raise PermisoInsuficiente("No puedes eliminar tu propio usuario.")
    if viejo["rol"] == ADMIN and sum(1 for e in almacen.coleccion("empleados") if e["rol"] == ADMIN) < 2:
        raise PermisoInsuficiente("Debe existir al menos un administrador.")

MENSAJE_ACCESO = "Datos no autorizados. Verifica tu nombre y documento."

def normalizar(s):
    """Minúsculas, sin tildes y con espacios colapsados."""
    s = unicodedata.normalize("NFD", str(s))
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").lower().split())


def autenticar(almacen, nombre, documento):
    """Devuelve una copia del registro del empleado o lanza AccesoDenegado. O(n)."""
    doc = re.sub(r"\D", "", str(documento))
    palabras = normalizar(nombre).split()
    if not doc or not palabras:
        raise AccesoDenegado(MENSAJE_ACCESO)
    emp = almacen.repo("empleados").obtener(doc)
    if emp is None or not all(p in normalizar(emp["nombre"]).split() for p in palabras):
        raise AccesoDenegado(MENSAJE_ACCESO)
    return dict(emp)


# Reglas copiadas de F.crud del HTML: ID solo dígitos (1-15), nombre obligatorio, ID único.
# Tipos de campo: id = identificador numérico, t = texto, e = correo, n = número >= 0, r = rol.

CAMPOS = {
    "clientes": [("id", "id"), ("nombre", "t"), ("tel", "t"), ("correo", "e")],
    "productos": [("id", "id"), ("nombre", "t"), ("cat", "t"), ("precio", "n"), ("cant", "n")],
    "proveedores": [("id", "id"), ("nombre", "t"), ("tel", "t"), ("correo", "e"), ("prods", "t")],
    "empleados": [("id", "id"), ("nombre", "t"), ("cargo", "t"), ("tel", "t"), ("correo", "e"), ("salario", "n"), ("rol", "r")],
}


class Repositorio:
    """CRUD con validaciones sobre una ListaLigada de diccionarios."""

    def __init__(self, nombre, lista, guardar):
        self.nombre, self._lista, self._guardar = nombre, lista, guardar

    def __len__(self):
        return len(self._lista)

    def listar(self):
        return self._lista.a_lista()

    def obtener(self, id_):
        """Devuelve el registro VIVO (mutable) o None."""
        return self._lista.buscar(lambda x: x["id"] == str(id_))

    def _normalizar(self, datos):
        o = {}
        for campo, tipo in CAMPOS[self.nombre]:
            x = str(datos.get(campo, "")).strip()
            if tipo == "n":
                try:
                    v = float(x) if x else 0
                except ValueError:
                    raise ErrorValidacion(f"'{campo}' debe ser un número.")
                if v < 0:
                    raise ErrorValidacion(f"'{campo}' no puede ser negativo.")
                x = int(v) if v == int(v) else v
            elif tipo == "e" and x and "@" not in x:
                raise ErrorValidacion("Correo inválido.")
            elif tipo == "r" and x not in ROLES_VALIDOS:
                raise ErrorValidacion("Rol inválido.")
            o[campo] = x
        if not re.fullmatch(r"\d{1,15}", o["id"]):
            raise ErrorValidacion("El identificador debe ser numérico (solo dígitos).")
        if not o["nombre"]:
            raise ErrorValidacion("El nombre es obligatorio.")
        return o

    def validar(self, datos, id_actual=None):
        o = self._normalizar(datos if id_actual is None else {**datos, "id": id_actual})
        if id_actual is None and self.obtener(o["id"]) is not None:
            raise ErrorValidacion("Ya existe un registro con ese identificador.")
        return o

    def agregar(self, datos):
        o = self.validar(datos)
        self._lista.agregar_final(o)
        self._guardar()
        return o

    def actualizar(self, id_, datos):
        if self.obtener(id_) is None:
            raise ErrorValidacion("Registro no encontrado.")
        o = self.validar(datos, id_actual=str(id_))
        self._lista.reemplazar(lambda x: x["id"] == str(id_), o)
        self._guardar()
        return o

    def eliminar(self, id_):
        if not self._lista.eliminar(lambda x: x["id"] == str(id_)):
            raise ErrorValidacion("Registro no encontrado.")
        self._guardar()

    def ordenado(self, campo="id"):
        tipo = dict(CAMPOS[self.nombre]).get(campo)
        if tipo is None:
            raise ErrorValidacion(f"Campo desconocido: {campo}")
        clave = (lambda x: float(x[campo])) if tipo in ("id", "n") else (lambda x: str(x[campo]).lower())
        return merge_sort(self._lista, clave).a_lista()

    def buscar_id_binaria(self, id_):
        filas = self.ordenado("id")
        i = busqueda_binaria(filas, int(id_), lambda x: int(x["id"]))
        return None if i < 0 else filas[i]

    def buscar_texto(self, texto):
        q = normalizar(texto)
        return [r for r in self._lista if q in normalizar(" ".join(str(v) for v in r.values()))]

# Compartidos por Ventas, Contabilidad y Administración (una sola implementación).

def estado_producto(p):
    return "Agotado" if p["cant"] <= 0 else "Pocas unidades" if p["cant"] <= 10 else "Disponible"


def matriz_ventas(almacen):
    """Unidades vendidas por producto (filas) y mes (columnas). Índices por diccionario: O(V·L + P)."""
    ventas = almacen.coleccion("ventas")
    periodos = sorted({v["fecha"][:7] for v in ventas})
    ids = [p["id"] for p in almacen.coleccion("productos")]
    col = {per: j for j, per in enumerate(periodos)}
    fila = {}
    for i, pid in enumerate(ids):
        fila.setdefault(pid, i)
    mx = [[0] * len(periodos) for _ in ids]
    for v in ventas:
        j = col[v["fecha"][:7]]
        for linea in v["items"]:
            i = fila.get(linea["pid"])
            if i is not None:
                mx[i][j] += linea["cant"]
    return {"periodos": periodos, "ids": ids, "matriz": mx}


def top_productos(almacen, n=5, m=None):
    """Los n más vendidos. Acepta una matriz ya calculada (m) para no recorrer las ventas dos veces."""
    m = m or matriz_ventas(almacen)
    nombres = {p["id"]: p["nombre"] for p in almacen.coleccion("productos")}
    filas = ListaLigada.desde({"pid": pid, "nombre": nombres[pid], "cant": sum(m["matriz"][i])} for i, pid in enumerate(m["ids"]))
    return merge_sort(filas, lambda x: -x["cant"]).a_lista()[:n]


def resumen_financiero(almacen):
    tot = {"Ingreso": 0, "Gasto": 0}
    for f in almacen.coleccion("fin"):
        if f["tipo"] in tot:
            tot[f["tipo"]] += f["monto"]
    return {"ingresos": tot["Ingreso"], "gastos": tot["Gasto"], "balance": tot["Ingreso"] - tot["Gasto"]}


def reporte_ventas(almacen):
    m = matriz_ventas(almacen)
    ventas = almacen.coleccion("ventas")
    return {"ventas": len(ventas), "total": sum(v["total"] for v in ventas),
            "unidades": sum(sum(f) for f in m["matriz"]), "top": top_productos(almacen, m=m), "matriz": m,
            "inventario": [(p["nombre"], p["cant"], estado_producto(p)) for p in almacen.coleccion("productos")]}

COLECCIONES = ("clientes", "productos", "proveedores", "empleados", "ventas", "compras", "fin", "movs")

_P = [(101, "Teclado mecánico", "Periféricos", 145000, 30), (102, "Mouse inalámbrico", "Periféricos", 65000, 50),
      (103, "Monitor 24 pulgadas", "Pantallas", 620000, 12), (104, "Disco SSD 480GB", "Almacenamiento", 210000, 25),
      (105, "Memoria RAM 8GB", "Componentes", 130000, 40), (106, "Silla ergonómica", "Mobiliario", 480000, 8),
      (107, "Webcam HD", "Periféricos", 95000, 20), (108, "Router WiFi 6", "Redes", 250000, 15)]
_VT = [[5, 8, 6], [12, 10, 15], [2, 3, 1], [7, 6, 9], [10, 11, 14], [1, 2, 0], [4, 5, 3], [3, 4, 6]]


def _emp(id_, nombre, cargo, salario, rol, tel="", correo=""):
    return {"id": id_, "nombre": nombre, "cargo": cargo, "tel": tel, "correo": correo, "salario": salario, "rol": rol}


def semilla():
    d = {
        "clientes": [{"id": "900100", "nombre": "Comercial Antioquia SAS", "tel": "3001112233", "correo": "compras@comercial.co"},
                     {"id": "43125678", "nombre": "María Gómez", "tel": "3109998877", "correo": "maria@correo.co"}],
        "productos": [{"id": str(i), "nombre": n, "cat": c, "precio": p, "cant": q} for i, n, c, p, q in _P],
        "proveedores": [{"id": "800200", "nombre": "TecnoImport SAS", "tel": "6044445566", "correo": "ventas@tecnoimport.co", "prods": "Periféricos, Componentes"},
                        {"id": "800300", "nombre": "Muebles Andinos", "tel": "6047778899", "correo": "info@andinos.co", "prods": "Mobiliario"}],
        "empleados": [_emp("1000", "Administrador", "Gerente", 0, "Administrador"),
                      _emp("1001", "Juan Pablo Vergara Henao", "Desarrollador", 0, "Administrador"),
                      _emp("1002", "Samuel Cañas López", "Desarrollador", 0, "Administrador"),
                      _emp("1003", "Ana Restrepo", "Vendedora", 2200000, "Ventas", "3001230000", "ana@empresa.co"),
                      _emp("1004", "Carlos Mejía", "Jefe de bodega", 2400000, "Bodega"),
                      _emp("1005", "Laura Pérez", "Contadora", 3200000, "Contabilidad"),
                      _emp("1006", "Diana Torres", "Gestora de talento humano", 3000000, "Recursos Humanos"),
                      _emp("1007", "Andrés Gil", "Comprador", 2800000, "Compras")],
        "ventas": [], "compras": [], "fin": [], "movs": [],
    }
    for j, per in enumerate(["2026-01", "2026-02", "2026-03"]):
        items = [{"pid": str(x[0]), "cant": _VT[i][j], "precio": x[3]} for i, x in enumerate(_P) if _VT[i][j]]
        total = sum(l["cant"] * l["precio"] for l in items)
        d["ventas"].append({"id": j + 1, "fecha": per + "-15", "party": "900100", "items": items, "total": total})
        d["fin"].append({"fecha": per + "-15", "tipo": "Ingreso", "concepto": f"Venta #{j + 1}", "monto": total})
    return d


def hoy():
    return date.today().isoformat()


class Almacen:
    def __init__(self, ruta=None):
        self.ruta = ruta
        if ruta and os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                self._cargar(json.load(f))
        else:
            self._cargar(semilla())
            self.guardar()

    def _cargar(self, d):
        self.colecciones = {c: ListaLigada.desde(d.get(c, [])) for c in COLECCIONES}
        self.despachos = ColaDinamica()   # ventas pendientes de despachar (FIFO)
        for x in d.get("despachos", []):
            self.despachos.encolar(x)
        self.ajustes = PilaDinamica()     # ajustes manuales reversibles (LIFO)
        for x in d.get("ajustes", []):
            self.ajustes.push(x)
        self._repos = {}

    def coleccion(self, nombre):
        return self.colecciones[nombre]

    def repo(self, nombre):
        if nombre not in CAMPOS:
            raise KeyError(nombre)
        if nombre not in self._repos:
            self._repos[nombre] = Repositorio(nombre, self.colecciones[nombre], self.guardar)
        return self._repos[nombre]

    def exportar(self):
        d = {c: self.colecciones[c].a_lista() for c in COLECCIONES}
        d["despachos"], d["ajustes"] = self.despachos.a_lista(), self.ajustes.a_lista()
        return d

    def guardar(self):
        if not self.ruta:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.ruta)), exist_ok=True)
        tmp = self.ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.exportar(), f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta)

    def importar(self, d):
        """Misma validación que el HTML: debe haber empleados y al menos un Administrador."""
        emps = d.get("empleados") if isinstance(d, dict) else None
        if not isinstance(emps, list) or not any(e.get("rol") == "Administrador" for e in emps):
            raise ErrorValidacion("Archivo de respaldo inválido.")
        self._cargar(d)
        self.guardar()

    def restablecer(self):
        self._cargar(semilla())
        self.guardar()
