import os
import sys

from Gestion.nucleo import Almacen, AccesoDenegado, autenticar
from roles import modulo_para

RUTA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos", "sige.json")


class Consola:
    """Entrada/salida por terminal. Los menús solo dependen de leer() y mostrar()."""

    def leer(self, prompt=""):
        return input(prompt)

    def mostrar(self, texto=""):
        print(texto)


def iniciar_sesion(almacen, io, intentos=3):
    """Pide nombre + documento. El rol lo decide el backend a partir del registro del empleado."""
    io.mostrar("SIGE · Sistema Integral de Gestión Empresarial\nIngreso del personal (acceso de prueba: Administrador / 1000)")
    for _ in range(intentos):
        nombre, documento = io.leer("Nombre completo: "), io.leer("Documento de identidad: ")
        try:
            return modulo_para(almacen, autenticar(almacen, nombre, documento), io)
        except AccesoDenegado as e:
            io.mostrar(str(e))
    io.mostrar("Demasiados intentos fallidos.")
    return None


def main(argv=None, almacen=None, io=None):
    argv = sys.argv[1:] if argv is None else argv
    almacen = almacen or Almacen(RUTA_DATOS)
    if "--web" in argv:
        from servidor import servir
        return servir(almacen)
    modulo = iniciar_sesion(almacen, io or Consola())
    if modulo:
        modulo.ejecutar_menu()


if __name__ == "__main__":
    main()
