"""Pruebas de estructuras de datos y algoritmos (no dependen de roles ni del servidor).
Ejecutar: python -m unittest test_base -v
"""
import unittest

from Gestion.estructuras import (ListaLigada, PilaDinamica, PilaEstatica, PilaVaciaError, PilaLlenaError,
                         ColaDinamica, ColaVaciaError, merge_sort, busqueda_binaria)

class TestListaLigada(unittest.TestCase):
    def test_agregar_y_recorrer(self):
        l = ListaLigada()
        l.agregar_final(2); l.agregar_final(3); l.agregar_inicio(1)
        self.assertEqual(l.a_lista(), [1, 2, 3]); self.assertEqual(len(l), 3)

    def test_vacia(self):
        l = ListaLigada()
        self.assertTrue(l.esta_vacia()); self.assertEqual(l.a_lista(), [])
        self.assertFalse(l.eliminar(lambda x: True)); self.assertIsNone(l.buscar(lambda x: True))

    def test_eliminar_cabeza_medio_cola_inexistente(self):
        l = ListaLigada.desde([1, 2, 3, 4])
        self.assertTrue(l.eliminar(lambda x: x == 1)); self.assertTrue(l.eliminar(lambda x: x == 3))
        self.assertTrue(l.eliminar(lambda x: x == 4)); self.assertFalse(l.eliminar(lambda x: x == 99))
        self.assertEqual(l.a_lista(), [2]); self.assertEqual(len(l), 1)

    def test_cola_se_actualiza_tras_eliminar_el_ultimo(self):
        l = ListaLigada.desde([1, 2]); l.eliminar(lambda x: x == 2); l.agregar_final(9)
        self.assertEqual(l.a_lista(), [1, 9])

    def test_eliminar_unico_y_reusar(self):
        l = ListaLigada.desde([5]); l.eliminar(lambda x: x == 5); l.agregar_final(6); l.agregar_inicio(4)
        self.assertEqual(l.a_lista(), [4, 6])

    def test_buscar_reemplazar_obtener(self):
        l = ListaLigada.desde(["a", "b"])
        self.assertEqual(l.buscar(lambda x: x == "b"), "b")
        self.assertTrue(l.reemplazar(lambda x: x == "a", "z")); self.assertFalse(l.reemplazar(lambda x: x == "q", "z"))
        self.assertEqual(l.obtener(0), "z")
        with self.assertRaises(IndexError): l.obtener(2)
        with self.assertRaises(IndexError): l.obtener(-1)


class TestPilas(unittest.TestCase):
    def _lifo(self, p):
        for x in (1, 2, 3): p.push(x)
        self.assertEqual(p.peek(), 3)
        self.assertEqual([p.pop(), p.pop(), p.pop()], [3, 2, 1]); self.assertTrue(p.esta_vacia())

    def test_dinamica_lifo(self): self._lifo(PilaDinamica())
    def test_estatica_lifo(self): self._lifo(PilaEstatica(5))

    def test_vacia_lanza_error(self):
        for p in (PilaDinamica(), PilaEstatica(2)):
            with self.assertRaises(PilaVaciaError): p.pop()
            with self.assertRaises(PilaVaciaError): p.peek()

    def test_estatica_llena_y_capacidad_invalida(self):
        p = PilaEstatica(2); p.push(1); p.push(2)
        self.assertTrue(p.esta_llena())
        with self.assertRaises(PilaLlenaError): p.push(3)
        p.pop(); p.push(7); self.assertEqual(p.a_lista(), [1, 7])
        with self.assertRaises(ValueError): PilaEstatica(0)

    def test_dinamica_sin_tope_y_a_lista(self):
        p = PilaDinamica()
        for i in range(10000): p.push(i)
        self.assertEqual(len(p), 10000); self.assertEqual(p.a_lista()[:3], [0, 1, 2])


class TestCola(unittest.TestCase):
    def test_fifo(self):
        c = ColaDinamica()
        for x in (1, 2, 3): c.encolar(x)
        self.assertEqual(c.frente(), 1); self.assertEqual([c.desencolar() for _ in range(3)], [1, 2, 3])

    def test_vacia_y_reuso(self):
        c = ColaDinamica()
        with self.assertRaises(ColaVaciaError): c.desencolar()
        with self.assertRaises(ColaVaciaError): c.frente()
        c.encolar(1); c.desencolar(); c.encolar(2)   # el puntero final debe reiniciarse
        self.assertEqual(c.a_lista(), [2]); self.assertEqual(len(c), 1)


class TestMergeSort(unittest.TestCase):
    def test_casos_basicos(self):
        for datos in ([], [1], [3, 1, 2], [1, 2, 3], [3, 2, 1], [2, 2, 1, 1]):
            self.assertEqual(merge_sort(ListaLigada.desde(datos)).a_lista(), sorted(datos))

    def test_estable_y_no_modifica_original(self):
        orig = ListaLigada.desde([(1, "a"), (0, "x"), (1, "b"), (0, "y")])
        r = merge_sort(orig, lambda t: t[0]).a_lista()
        self.assertEqual(r, [(0, "x"), (0, "y"), (1, "a"), (1, "b")])
        self.assertEqual(orig.a_lista()[0], (1, "a"))

    def test_lista_grande_y_cola_valida(self):
        datos = [(i * 7919) % 10007 for i in range(10000)]
        r = merge_sort(ListaLigada.desde(datos)); self.assertEqual(r.a_lista(), sorted(datos))
        r.agregar_final(10 ** 9); self.assertEqual(r.a_lista()[-1], 10 ** 9)


class TestBusquedaBinaria(unittest.TestCase):
    def test_encuentra_y_no_encuentra(self):
        s = [1, 3, 5, 7, 9]
        self.assertEqual([busqueda_binaria(s, x) for x in s], [0, 1, 2, 3, 4])
        self.assertEqual(busqueda_binaria(s, 4), -1); self.assertEqual(busqueda_binaria(s, 0), -1)
        self.assertEqual(busqueda_binaria(s, 10), -1); self.assertEqual(busqueda_binaria([], 1), -1)
        self.assertEqual(busqueda_binaria([5], 5), 0)


if __name__ == "__main__":
    unittest.main()
