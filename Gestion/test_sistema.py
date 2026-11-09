"""Pruebas del sistema completo: autenticación, roles, reglas de negocio, persistencia y arranque.
Requiere roles.py y servidor.py. Ejecutar: python -m unittest test_sistema -v
"""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import main
from Gestion.nucleo import Almacen, autenticar, AccesoDenegado, PermisoInsuficiente, ErrorNegocio, ErrorValidacion
from roles import modulo_para, ROLES
from servidor import crear_servidor

class Base(unittest.TestCase):
    def setUp(self):
        self.a = Almacen()

    def rol(self, nombre, doc):
        return modulo_para(self.a, autenticar(self.a, nombre, doc))

    def stock(self, pid):
        return self.a.repo("productos").obtener(pid)["cant"]


class TestPermisos(Base):
    def test_cada_rol_solo_sus_modulos(self):
        casos = {("Ana Restrepo", "1003"): ["clientes", "productos", "ventas", "reportes"],
                 ("Carlos Mejía", "1004"): ["productos", "inventario"],
                 ("Laura Pérez", "1005"): ["finanzas", "reportes"],
                 ("Diana Torres", "1006"): ["empleados"],
                 ("Andrés Gil", "1007"): ["proveedores", "productos", "inventario", "compras"]}
        todos = ["clientes", "productos", "inventario", "proveedores", "ventas", "compras", "empleados", "finanzas", "reportes", "admin"]
        for (n, d), ok in casos.items():
            m = self.rol(n, d)
            for mod in todos:
                if mod in ok: m.requerir(mod)
                else:
                    with self.assertRaises(PermisoInsuficiente, msg=f"{m.rol}->{mod}"): m.requerir(mod)

    def test_solo_lectura(self):
        with self.assertRaises(PermisoInsuficiente): self.rol("Ana Restrepo", "1003").crear("productos", {"id": "1", "nombre": "x"})
        # Compras ve inventario en solo lectura: el backend rechaza escribir en él
        with self.assertRaises(PermisoInsuficiente): self.rol("Andrés Gil", "1007").requerir("inventario", True)
        self.assertFalse(hasattr(self.rol("Andrés Gil", "1007"), "registrar_movimiento"))
        with self.assertRaises(PermisoInsuficiente): self.rol("Carlos Mejía", "1004").eliminar("productos", "101")

    def test_operaciones_de_otro_rol_no_existen_en_el_modulo(self):
        # Un rol ni siquiera tiene los métodos de otro rol (no es solo un chequeo en tiempo de ejecución)
        self.assertFalse(hasattr(self.rol("Laura Pérez", "1005"), "registrar_venta"))
        self.assertFalse(hasattr(self.rol("Ana Restrepo", "1003"), "registrar_finanza"))
        self.assertFalse(hasattr(self.rol("Carlos Mejía", "1004"), "exportar_respaldo"))
        with self.assertRaises(PermisoInsuficiente): self.rol("Diana Torres", "1006").listar("clientes")
        with self.assertRaises(PermisoInsuficiente): self.rol("Ana Restrepo", "1003").listar("empleados")

    def test_admin_todo(self):
        m = self.rol("Administrador", "1000")
        for mod in ["clientes", "inventario", "ventas", "compras", "empleados", "finanzas", "admin"]: m.requerir(mod, True)


class TestVentasCompras(Base):
    def test_venta_descuenta_stock_registra_ingreso_y_encola(self):
        m = self.rol("Ana Restrepo", "1003"); antes = self.stock("101"); n_fin = len(self.a.coleccion("fin"))
        v = m.registrar_venta("900100", [{"pid": "101", "cant": 2}])
        self.assertEqual(self.stock("101"), antes - 2); self.assertEqual(v["total"], 290000)
        self.assertEqual(len(self.a.coleccion("fin")), n_fin + 1); self.assertEqual(self.a.despachos.frente()["venta"], v["id"])
        self.assertEqual(v["id"], 4)

    def test_venta_sin_existencias_no_cambia_nada(self):
        m = self.rol("Ana Restrepo", "1003"); antes = self.stock("106")
        with self.assertRaises(ErrorNegocio): m.registrar_venta("900100", [{"pid": "106", "cant": 5}, {"pid": "106", "cant": 5}])
        self.assertEqual(self.stock("106"), antes); self.assertEqual(len(self.a.despachos), 0)

    def test_venta_validaciones(self):
        m = self.rol("Ana Restrepo", "1003")
        for cli, items in (("0", [{"pid": "101", "cant": 1}]), ("900100", []), ("900100", [{"pid": "999", "cant": 1}]),
                           ("900100", [{"pid": "101", "cant": 0}]), ("900100", [{"pid": "101", "cant": "x"}])):
            with self.assertRaises(ErrorNegocio): m.registrar_venta(cli, items)

    def test_compra_suma_stock_y_gasto(self):
        m = self.rol("Andrés Gil", "1007"); antes = self.stock("102")
        c = m.registrar_compra("800200", [{"pid": "102", "cant": 10, "precio": 50000}])
        self.assertEqual(self.stock("102"), antes + 10); self.assertEqual(c["total"], 500000)
        self.assertEqual(self.a.coleccion("fin").a_lista()[-1]["tipo"], "Gasto")
        with self.assertRaises(ErrorNegocio): m.registrar_compra("800200", [{"pid": "102", "cant": 1, "precio": 0}])
        with self.assertRaises(ErrorNegocio): m.registrar_compra("1", [{"pid": "102", "cant": 1, "precio": 5}])


class TestBodega(Base):
    def test_movimiento_y_deshacer_lifo(self):
        m = self.rol("Carlos Mejía", "1004"); base = self.stock("101")
        m.registrar_movimiento("101", "Entrada", 5); m.registrar_movimiento("101", "Salida", 2)
        self.assertEqual(self.stock("101"), base + 3)
        self.assertEqual(m.deshacer_ultimo_ajuste()["tipo"], "Salida"); self.assertEqual(self.stock("101"), base + 5)
        m.deshacer_ultimo_ajuste(); self.assertEqual(self.stock("101"), base)
        with self.assertRaises(ErrorNegocio): m.deshacer_ultimo_ajuste()

    def test_movimientos_invalidos(self):
        m = self.rol("Carlos Mejía", "1004")
        for args in (("101", "Salida", 9999), ("101", "Otro", 1), ("101", "Entrada", 0), ("999", "Entrada", 1), ("101", "Entrada", "a")):
            with self.assertRaises(ErrorNegocio): m.registrar_movimiento(*args)

    def test_no_deshace_entrada_si_ya_se_vendio(self):
        b = self.rol("Carlos Mejía", "1004"); b.registrar_movimiento("106", "Entrada", 100)
        self.rol("Ana Restrepo", "1003").registrar_venta("900100", [{"pid": "106", "cant": 60}])
        with self.assertRaises(ErrorNegocio): b.deshacer_ultimo_ajuste()
        self.assertEqual(len(self.a.ajustes), 1)

    def test_despacho_fifo(self):
        v = self.rol("Ana Restrepo", "1003"); b = self.rol("Carlos Mejía", "1004")
        with self.assertRaises(ErrorNegocio): b.despachar_siguiente()
        v.registrar_venta("900100", [{"pid": "101", "cant": 1}]); v.registrar_venta("900100", [{"pid": "102", "cant": 1}])
        self.assertEqual([b.despachar_siguiente()["venta"], b.despachar_siguiente()["venta"]], [4, 5])


class TestContabilidadRRHH(Base):
    def test_finanzas(self):
        m = self.rol("Laura Pérez", "1005"); antes = m.resumen_financiero()["balance"]
        m.registrar_finanza("Gasto", "Papelería", 1000); self.assertEqual(m.resumen_financiero()["balance"], antes - 1000)
        for args in (("Otro", "x", 1), ("Gasto", " ", 1), ("Gasto", "x", 0), ("Gasto", "x", "a")):
            with self.assertRaises(ErrorNegocio): m.registrar_finanza(*args)

    def test_rrhh_gestiona_empleados_pero_no_administradores(self):
        m = self.rol("Diana Torres", "1006")
        m.crear("empleados", {"id": "2000", "nombre": "Nuevo Empleado", "rol": "Ventas"})
        for datos in ({"id": "2001", "nombre": "Falso Admin", "rol": "Administrador"},):
            with self.assertRaises(PermisoInsuficiente): m.crear("empleados", datos)
        with self.assertRaises(PermisoInsuficiente): m.eliminar("empleados", "1000")
        with self.assertRaises(PermisoInsuficiente): m.eliminar("empleados", "1006")
        with self.assertRaises(PermisoInsuficiente): m.editar("empleados", "1006", {"nombre": "Diana Torres", "rol": "Ventas"})
        with self.assertRaises(PermisoInsuficiente): m.editar("empleados", "1000", {"nombre": "Administrador", "rol": "Ventas"})
        m.eliminar("empleados", "2000")

    def test_validaciones_crud(self):
        m = self.rol("Diana Torres", "1006")
        for d in ({"id": "abc", "nombre": "x", "rol": "Ventas"}, {"id": "2000", "nombre": "", "rol": "Ventas"},
                  {"id": "1004", "nombre": "Dup", "rol": "Ventas"}, {"id": "2000", "nombre": "x", "rol": "Jefe"},
                  {"id": "2000", "nombre": "x", "rol": "Ventas", "salario": "-5"}, {"id": "2000", "nombre": "x", "rol": "Ventas", "correo": "sin-arroba"}):
            with self.assertRaises(ErrorValidacion): m.crear("empleados", d)
        with self.assertRaises(ErrorValidacion): m.eliminar("empleados", "7777")

    def test_login_valido_tras_crear_empleado(self):
        self.rol("Diana Torres", "1006").crear("empleados", {"id": "2000", "nombre": "Pedro Ruiz", "rol": "Bodega"})
        self.assertEqual(self.rol("Pedro Ruiz", "2000").rol, "Bodega")


class TestAdminYPersistencia(Base):
    def test_admin_no_puede_quitarse_rol_ni_eliminarse_ni_dejar_sin_admin(self):
        m = self.rol("Administrador", "1000")
        with self.assertRaises(PermisoInsuficiente): m.editar("empleados", "1000", {"nombre": "Administrador", "rol": "Ventas"})
        with self.assertRaises(PermisoInsuficiente): m.eliminar("empleados", "1000")

    def test_ultimo_admin_no_se_elimina(self):
        m = self.rol("Administrador", "1000")
        m.eliminar("empleados", "1001"); m.eliminar("empleados", "1002")
        # 1000 es el único admin y es el propio usuario: bloqueado por ambas reglas
        with self.assertRaises(PermisoInsuficiente): m.eliminar("empleados", "1000")

    def test_respaldo_ida_y_vuelta(self):
        m = self.rol("Administrador", "1000"); r = json.loads(json.dumps(m.exportar_respaldo()))
        m.eliminar("clientes", "900100"); m.importar_respaldo(r)
        self.assertIsNotNone(self.a.repo("clientes").obtener("900100"))
        with self.assertRaises(ErrorValidacion): m.importar_respaldo({"empleados": [{"rol": "Ventas"}]})
        with self.assertRaises(ErrorValidacion): m.importar_respaldo([])

    def test_restablecer(self):
        m = self.rol("Administrador", "1000"); m.eliminar("clientes", "900100"); m.restablecer_datos()
        self.assertEqual(len(self.a.repo("clientes")), 2)

    def test_persistencia_json_incluye_cola_y_pila(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = os.path.join(d, "s.json"); a = Almacen(ruta)
            m = modulo_para(a, autenticar(a, "Ana Restrepo", "1003")); m.registrar_venta("900100", [{"pid": "101", "cant": 1}])
            b = modulo_para(a, autenticar(a, "Carlos Mejía", "1004")); b.registrar_movimiento("101", "Entrada", 3)
            a2 = Almacen(ruta)
            self.assertEqual(len(a2.despachos), 1); self.assertEqual(len(a2.ajustes), 1)
            self.assertEqual(len(a2.coleccion("ventas")), 4)

    def test_listar_ordenar_y_buscar(self):
        m = self.rol("Administrador", "1000")
        self.assertEqual([p["id"] for p in m.listar("productos", "precio")][:2], ["102", "107"])
        self.assertEqual([p["id"] for p in m.listar("productos", "nombre")][0], "104")
        self.assertEqual(m.listar("productos", texto="104")[0]["nombre"], "Disco SSD 480GB")
        self.assertEqual(m.listar("productos", texto="999"), [])
        self.assertEqual(len(m.listar("clientes", texto="maria")), 1)
        with self.assertRaises(ErrorValidacion): m.listar("productos", "inexistente")

    def test_reportes(self):
        r = self.rol("Ana Restrepo", "1003").reportes()
        self.assertEqual(r["ventas"], 3); self.assertEqual(r["top"][0]["pid"], "102")
        self.assertEqual(r["unidades"], sum(sum(f) for f in [[5,8,6],[12,10,15],[2,3,1],[7,6,9],[10,11,14],[1,2,0],[4,5,3],[3,4,6]]))


class TestLogin(Base):
    def test_credenciales_validas(self):
        self.assertEqual(autenticar(self.a, "Administrador", "1000")["rol"], "Administrador")

    def test_id_lleva_al_rol_correspondiente(self):
        esperado = {"1004": ("Carlos Mejía", "Bodega"), "1005": ("Laura Pérez", "Contabilidad"),
                    "1006": ("Diana Torres", "Recursos Humanos"), "1007": ("Andrés Gil", "Compras"),
                    "1003": ("Ana Restrepo", "Ventas")}
        for doc, (nombre, rol) in esperado.items():
            m = modulo_para(self.a, autenticar(self.a, nombre, doc))
            self.assertEqual(m.rol, rol); self.assertIsInstance(m, ROLES[rol])

    def test_nombre_sin_tildes_y_mayusculas(self):
        self.assertEqual(autenticar(self.a, "carlos mejia", " 1004 ")["id"], "1004")

    def test_id_inexistente(self):
        with self.assertRaises(AccesoDenegado): autenticar(self.a, "Carlos Mejía", "9999")

    def test_credenciales_incorrectas(self):
        for n, d in (("Otra Persona", "1004"), ("Carlos Mejía", "1005"), ("", "1004"), ("Carlos", ""), ("Carlos", "abc")):
            with self.assertRaises(AccesoDenegado): autenticar(self.a, n, d)

    def test_id_solo_no_basta(self):
        with self.assertRaises(AccesoDenegado): autenticar(self.a, "   ", "1000")

    def test_mensaje_no_revela_si_el_id_existe(self):
        try: autenticar(self.a, "x", "9999")
        except AccesoDenegado as e1: m1 = str(e1)
        try: autenticar(self.a, "x", "1004")
        except AccesoDenegado as e2: m2 = str(e2)
        self.assertEqual(m1, m2)

    def test_rol_sin_modulo(self):
        with self.assertRaises(AccesoDenegado): modulo_para(self.a, {"id": "1", "nombre": "x", "rol": "Inventado"})

    def test_modulo_rechaza_usuario_de_otro_rol(self):
        with self.assertRaises(AccesoDenegado): ROLES["Bodega"](self.a, {"id": "1000", "nombre": "A", "rol": "Ventas"})


class Falsa:
    def __init__(self, entradas): self.e, self.s = list(entradas), []
    def leer(self, p=""): self.s.append(p); return self.e.pop(0)
    def mostrar(self, t=""): self.s.append(str(t))
    def texto(self): return "\n".join(self.s)


class TestMain(unittest.TestCase):
    def test_login_y_menu_bodega(self):
        io = Falsa(["Carlos Mejía", "1004", "2", "1", "0", "0", "0"])  # Inventario -> ver -> volver -> salir
        main.main([], Almacen(), io)
        t = io.texto(); self.assertIn("Rol: Bodega", t); self.assertIn("Inventario", t); self.assertNotIn("Finanzas", t)

    def test_tres_intentos_fallidos(self):
        io = Falsa(["x", "1", "x", "2", "x", "3"]); main.main([], Almacen(), io)
        self.assertIn("Demasiados intentos", io.texto())

    def test_venta_por_consola_y_error_controlado(self):
        io = Falsa(["Ana Restrepo", "1003", "3", "1", "900100", "101", "1", "n", "1", "000", "101", "1", "n", "0", "0", "0"])
        # menú Ventas: opciones -> clientes(1) productos(2) ventas(3) reportes(4)
        main.main([], Almacen(), io); t = io.texto()
        self.assertIn("Venta #4 registrada", t); self.assertIn("Error: Cliente no encontrado.", t)


class TestServidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = crear_servidor(Almacen(), port=0); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls): cls.srv.shutdown(); cls.srv.server_close()

    def post(self, obj):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/login", json.dumps(obj).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.load(r)
        except urllib.error.HTTPError as e: return e.code, json.load(e)

    def test_login_ok_devuelve_rol_y_modulos(self):
        st, r = self.post({"nombre": "Laura Pérez", "documento": "1005"})
        self.assertEqual(st, 200); self.assertEqual(r["usuario"]["rol"], "Contabilidad"); self.assertEqual(r["modulos"], ["inicio", "finanzas", "reportes"])

    def test_login_rechazado(self):
        self.assertEqual(self.post({"nombre": "Laura Pérez", "documento": "9999"})[0], 401)
        self.assertEqual(self.post({"nombre": "Otro", "documento": "1005"})[0], 401)
        self.assertEqual(self.post({})[0], 401)


if __name__ == "__main__":
    unittest.main()
