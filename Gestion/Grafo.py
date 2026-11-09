import math
import tkinter as tk
from tkinter import messagebox

class VerticeAislado:
    def __init__(self, id_nodo, etiqueta, tipo):
        self.id = id_nodo
        self.etiqueta = etiqueta
        self.tipo = tipo  # "Producto", "Categoria", "Bodega"
        self.vecinos = []

class GrafoIndependiente:
    def __init__(self):
        self.nodos = {}  # Mantiene sus propios vértices aislados

    def agregar_vertice(self, id_nodo, etiqueta, tipo):
        if id_nodo not in self.nodos:
            self.nodos[id_nodo] = VerticeAislado(id_nodo, etiqueta, tipo)

    def conectar(self, id1, id2):
        if id1 in self.nodos and id2 in self.nodos:
            n1, n2 = self.nodos[id1], self.nodos[id2]
            if n2 not in n1.vecinos: n1.vecinos.append(n2)
            if n1 not in n2.vecinos: n2.vecinos.append(n1)

class InterfazGrafoAislado:
    def __init__(self, root, grafo):
        self.root = root
        self.grafo = grafo
        self.root.title("Grafo Relacional Desconectado del Árbol")
        self.root.geometry("850x600")

        # Panel Superior de Controles
        frame_top = tk.Frame(self.root, padx=10, pady=10)
        frame_top.pack(fill=tk.X)

        btn_cargar = tk.Button(
            frame_top, 
            text="Cargar Grafo Aislado Demo", 
            command=self.cargar_demo, 
            bg="#27AE60", 
            fg="white", 
            font=("Arial", 9, "bold")
        )
        btn_cargar.pack(side=tk.LEFT, padx=5)

        # Lienzo independiente para el dibujo
        self.canvas = tk.Canvas(self.root, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def cargar_demo(self):
        # Nodos exclusivos del Grafo
        nodos = [
            (10, "Electrónica", "Categoria"),
            (20, "Muebles", "Categoria"),
            (100, "Pasillo A", "Bodega"),
            (200, "Pasillo B", "Bodega"),
            (500, "Laptop", "Producto"),
            (501, "Silla", "Producto")
        ]
        
        # Conexiones internas (aristas entre sus propios nodos)
        aristas = [
            (500, 10), (500, 100),
            (501, 20), (501, 200)
        ]

        for i, e, t in nodos:
            self.grafo.agregar_vertice(i, e, t)
        for origen, destino in aristas:
            self.grafo.conectar(origen, destino)

        self.dibujar()

    def dibujar(self):
        self.canvas.delete("all")
        nodos = list(self.grafo.nodos.values())
        total = len(nodos)
        if total == 0:
            return

        cx, cy, r_dist = 400, 270, 180
        pos = {}

        # Calcular posiciones dinámicas en círculo
        for i, n in enumerate(nodos):
            ang = 2 * math.pi * i / total
            pos[n.id] = (cx + r_dist * math.cos(ang), cy + r_dist * math.sin(ang))

        # 1. Dibujar Aristas del grafo
        visitados = set()
        for n in nodos:
            x1, y1 = pos[n.id]
            for v in n.vecinos:
                par = tuple(sorted([n.id, v.id]))
                if par not in visitados:
                    x2, y2 = pos[v.id]
                    self.canvas.create_line(x1, y1, x2, y2, width=2, fill="#888888")
                    visitados.add(par)

        # 2. Dibujar Vértices independientes
        colores = {"Producto": "#CAF3F1", "Categoria": "#D4F7DC", "Bodega": "#FADBD8"}
        bordes = {"Producto": "#2C69A1", "Categoria": "#27AE60", "Bodega": "#C0392B"}

        for n in nodos:
            x, y = pos[n.id]
            c_fill = colores.get(n.tipo, "#FFF")
            c_out = bordes.get(n.tipo, "#000")

            self.canvas.create_oval(x - 26, y - 26, x + 26, y + 26, fill=c_fill, outline=c_out, width=2)
            self.canvas.create_text(x, y - 4, text=str(n.id), font=("Arial", 8, "bold"))
            self.canvas.create_text(x, y + 10, text=n.etiqueta[:9], font=("Arial", 7, "bold"))

if __name__ == "__main__":
    root = tk.Tk()
    grafo_aislado = GrafoIndependiente()
    app = InterfazGrafoAislado(root, grafo_aislado)
    root.mainloop()
