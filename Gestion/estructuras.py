class Nodo:
    __slots__ = ("dato", "sig")

    def __init__(self, dato, sig=None):
        self.dato = dato
        self.sig = sig


class ListaLigada:
    def __init__(self):
        self._cabeza = None
        self._cola = None
        self._n = 0

    @classmethod
    def desde(cls, iterable):
        lista = cls()
        for x in iterable:
            lista.agregar_final(x)
        return lista

    @classmethod
    def desde_nodos(cls, cabeza):
        """Construye una lista a partir de una cadena de nodos ya enlazados. O(n)."""
        lista = cls()
        lista._cabeza = cabeza
        actual, ultimo, n = cabeza, None, 0
        while actual is not None:
            ultimo, n, actual = actual, n + 1, actual.sig
        lista._cola, lista._n = ultimo, n
        return lista

    def __len__(self):
        return self._n

    def __iter__(self):
        actual = self._cabeza
        while actual is not None:
            yield actual.dato
            actual = actual.sig

    def esta_vacia(self):
        return self._n == 0

    def agregar_final(self, dato):
        nodo = Nodo(dato)
        if self._cola is None:
            self._cabeza = self._cola = nodo
        else:
            self._cola.sig = nodo
            self._cola = nodo
        self._n += 1

    def agregar_inicio(self, dato):
        self._cabeza = Nodo(dato, self._cabeza)
        if self._cola is None:
            self._cola = self._cabeza
        self._n += 1

    def obtener(self, indice):
        if indice < 0 or indice >= self._n:
            raise IndexError("Índice fuera de rango")
        actual = self._cabeza
        for _ in range(indice):
            actual = actual.sig
        return actual.dato

    def buscar(self, predicado):
        """Primer dato que cumple el predicado, o None."""
        for x in self:
            if predicado(x):
                return x
        return None

    def reemplazar(self, predicado, nuevo):
        actual = self._cabeza
        while actual is not None:
            if predicado(actual.dato):
                actual.dato = nuevo
                return True
            actual = actual.sig
        return False

    def eliminar(self, predicado):
        """Elimina el primer nodo que cumple el predicado. Devuelve True si eliminó."""
        previo, actual = None, self._cabeza
        while actual is not None:
            if predicado(actual.dato):
                if previo is None:
                    self._cabeza = actual.sig
                else:
                    previo.sig = actual.sig
                if actual is self._cola:
                    self._cola = previo
                self._n -= 1
                return True
            previo, actual = actual, actual.sig
        return False

    def a_lista(self):
        return list(self)

class PilaVaciaError(IndexError):
    pass


class PilaLlenaError(OverflowError):
    pass


class _PilaBase:
    """Comportamiento común de ambas pilas (_n = número de elementos)."""
    _n = 0

    def __len__(self):
        return self._n

    def esta_vacia(self):
        return self._n == 0


class PilaDinamica(_PilaBase):
    def __init__(self):
        self._tope = None

    def push(self, dato):
        self._tope = Nodo(dato, self._tope)
        self._n += 1

    def pop(self):
        dato = self.peek()
        self._tope = self._tope.sig
        self._n -= 1
        return dato

    def peek(self):
        if self._tope is None:
            raise PilaVaciaError("La pila está vacía")
        return self._tope.dato

    def a_lista(self):
        """Del fondo hacia el tope (permite reconstruirla con push en ese orden)."""
        datos, actual = [], self._tope
        while actual is not None:
            datos.append(actual.dato)
            actual = actual.sig
        datos.reverse()
        return datos


class PilaEstatica(_PilaBase):
    def __init__(self, capacidad):
        if capacidad < 1:
            raise ValueError("La capacidad debe ser al menos 1")
        self._datos = [None] * capacidad

    @property
    def capacidad(self):
        return len(self._datos)

    def esta_llena(self):
        return self._n == len(self._datos)

    def push(self, dato):
        if self.esta_llena():
            raise PilaLlenaError("La pila está llena")
        self._datos[self._n] = dato
        self._n += 1

    def pop(self):
        dato = self.peek()
        self._n -= 1
        self._datos[self._n] = None
        return dato

    def peek(self):
        if self._n == 0:
            raise PilaVaciaError("La pila está vacía")
        return self._datos[self._n - 1]

    def a_lista(self):
        return self._datos[: self._n]

class ColaVaciaError(IndexError):
    pass


class ColaDinamica:
    """FIFO dinámica: la cantidad de despachos pendientes no tiene un máximo razonable."""

    def __init__(self):
        self._frente = None
        self._fin = None
        self._n = 0

    def __len__(self):
        return self._n

    def esta_vacia(self):
        return self._n == 0

    def encolar(self, dato):
        nodo = Nodo(dato)
        if self._fin is None:
            self._frente = self._fin = nodo
        else:
            self._fin.sig = nodo
            self._fin = nodo
        self._n += 1

    def desencolar(self):
        dato = self.frente()
        self._frente = self._frente.sig
        if self._frente is None:
            self._fin = None
        self._n -= 1
        return dato

    def frente(self):
        if self._frente is None:
            raise ColaVaciaError("La cola está vacía")
        return self._frente.dato

    def a_lista(self):
        datos, actual = [], self._frente
        while actual is not None:
            datos.append(actual.dato)
            actual = actual.sig
        return datos

def _dividir(cabeza):
    lento, rapido = cabeza, cabeza.sig
    while rapido is not None and rapido.sig is not None:
        lento, rapido = lento.sig, rapido.sig.sig
    segunda, lento.sig = lento.sig, None
    return cabeza, segunda


def _mezclar(a, b, clave):
    ficticio = Nodo(None)
    cola = ficticio
    while a is not None and b is not None:
        if clave(a.dato) <= clave(b.dato):  # <= mantiene la estabilidad
            cola.sig, a = a, a.sig
        else:
            cola.sig, b = b, b.sig
        cola = cola.sig
    cola.sig = a if a is not None else b
    return ficticio.sig


def _ordenar(cabeza, clave):
    if cabeza is None or cabeza.sig is None:  # caso base
        return cabeza
    izq, der = _dividir(cabeza)
    return _mezclar(_ordenar(izq, clave), _ordenar(der, clave), clave)


def merge_sort(lista, clave=lambda x: x):
    """Devuelve una ListaLigada NUEVA ordenada ascendentemente. No modifica la original. O(n log n)."""
    copia = ListaLigada.desde(lista)
    return ListaLigada.desde_nodos(_ordenar(copia._cabeza, clave))


def busqueda_binaria(seq, objetivo, clave=lambda x: x, bajo=0, alto=None):
    """Índice del elemento cuya clave es 'objetivo' o -1. 'seq' debe estar ordenada por 'clave'."""
    if alto is None:
        alto = len(seq) - 1
    if bajo > alto:
        return -1
    medio = (bajo + alto) // 2
    valor = clave(seq[medio])
    if valor == objetivo:
        return medio
    if valor < objetivo:
        return busqueda_binaria(seq, objetivo, clave, medio + 1, alto)
    return busqueda_binaria(seq, objetivo, clave, bajo, medio - 1)
