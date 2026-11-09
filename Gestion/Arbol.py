import tkinter as tk
from tkinter import messagebox

class NodoGestion:
    def __init__(self, clave, datos):
        self.clave = clave
        self.datos = datos
        self.izq = None
        self.der = None

class ArbolAdministrativo:
    def __init__(self):
        self.raiz = None

    def registrar(self, clave, datos):
        nuevo = NodoGestion(clave, datos)
        if not self.raiz:
            self.raiz = nuevo
            return True

        actual = self.raiz
        while True:
            if clave < actual.clave:
                if not actual.izq:
                    actual.izq = nuevo
                    return True
                actual = actual.izq
            elif clave > actual.clave:
                if not actual.der:
                    actual.der = nuevo
                    return True
                actual = actual.der
            else:
                actual.datos = datos
                return False

    def consultar(self, clave):
        actual = self.raiz
        while actual:
            if clave == actual.clave:
                return actual.datos
            actual = actual.izq if clave < actual.clave else actual.der
        return None

class InterfazPruebasArbol:
    def __init__(self, root, arbol):
        self.root = root
        self.arbol = arbol
        self.root.title("Pruebas de Sistema - Visualizador de Árbol Binario")
        self.root.geometry("900x650")

        # Panel de Controles
        frame_controles = tk.Frame(self.root, bg="#f0f0f0", bd=2, relief=tk.GROOVE)
        frame_controles.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Label(
            frame_controles, text="ID / Código:", bg="#f0f0f0", font=("Arial", 10, "bold")
        ).grid(row=0, column=0, padx=5, pady=5)
        self.entry_clave = tk.Entry(frame_controles, width=10)
        self.entry_clave.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(
            frame_controles, text="Nombre / Detalle:", bg="#f0f0f0", font=("Arial", 10, "bold")
        ).grid(row=0, column=2, padx=5, pady=5)
        self.entry_datos = tk.Entry(frame_controles, width=20)
        self.entry_datos.grid(row=0, column=3, padx=5, pady=5)

        btn_insertar = tk.Button(
            frame_controles,
            text="Insertar Producto",
            command=self.insertar_nodo,
            bg="#2C69A1",
            fg="white",
            font=("Arial", 9, "bold"),
        )
        btn_insertar.grid(row=0, column=4, padx=10, pady=5)

        btn_buscar = tk.Button(
            frame_controles,
            text="Buscar ID",
            command=self.buscar_nodo,
            bg="#E0850D",
            fg="white",
            font=("Arial", 9, "bold"),
        )
        btn_buscar.grid(row=0, column=5, padx=5, pady=5)

        btn_precargar = tk.Button(
            frame_controles,
            text="Precargar Productos de Prueba",
            command=self.cargar_datos_demo,
            bg="#9B9595",
            fg="white",
            font=("Arial", 9, "bold"),
        )
        btn_precargar.grid(row=0, column=6, padx=20, pady=5)

        # Lienzo de Dibujo
        self.canvas = tk.Canvas(self.root, bg="white", bd=2, relief=tk.SUNKEN)
        self.canvas.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=10)

    def insertar_nodo(self):
        try:
            clave = int(self.entry_clave.get())
            datos = self.entry_datos.get().strip()
            if not datos:
                messagebox.showwarning("Advertencia", "Por favor ingresa un nombre para el producto.")
                return

            self.arbol.registrar(clave, {"nombre": datos})
            self.actualizar_grafico()
            self.entry_clave.delete(0, tk.END)
            self.entry_datos.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "El ID debe ser un número entero.")

    def buscar_nodo(self):
        try:
            clave = int(self.entry_clave.get())
            resultado = self.arbol.consultar(clave)
            if resultado:
                messagebox.showinfo("Resultado de Búsqueda", f"ID: {clave}\nProducto: {resultado['nombre']}")
            else:
                messagebox.showwarning("No encontrado", f"El ID {clave} no existe en el sistema.")
        except ValueError:
            messagebox.showerror("Error", "Ingresa un ID válido para buscar.")

    def cargar_datos_demo(self):
        # Productos típicos de un sistema administrativo ordenados para balancear el árbol de pruebas
        productos_prueba = [
            (101, "RAM 32"),
            (100, "Laptop Corporativa"),
            (50, "Teclado USB"),
            (150, "Monitor 4K"),
            (25, "Mouse Óptico"),
            (75, "Impresora Láser"),
            (125, "Disco Duro SSD"),
            (175, "Licencia Windows Pro"),
            (185, "Tarjeta grafica"),
            (200, "Teclado magnectico"),
            (205, "HDMI")
        ]
        for clave, nombre in productos_prueba:
            self.arbol.registrar(clave, {"nombre": nombre})
        self.actualizar_grafico()

    def actualizar_grafico(self):
        self.canvas.delete("all")
        if self.arbol.raiz:
            self.dibujar_nodo(self.arbol.raiz, 450, 50, 200, 60)

    def dibujar_nodo(self, nodo, x, y, espaciado_x, espaciado_y):
        # Dibujar enlaces a los hijos primero (para que queden detrás de los círculos)
        if nodo.izq:
            self.canvas.create_line(x, y, x - espaciado_x, y + espaciado_y, width=2, fill="#1A1818")
            self.dibujar_nodo(nodo.izq, x - espaciado_x, y + espaciado_y, espaciado_x * 0.5, espaciado_y)

        if nodo.der:
            self.canvas.create_line(x, y, x + espaciado_x, y + espaciado_y, width=2, fill="#1A1818")
            self.dibujar_nodo(nodo.der, x + espaciado_x, y + espaciado_y, espaciado_x * 0.5, espaciado_y)

        # Dibujar el nodo actual (Círculo)
        radio = 24
        self.canvas.create_oval(x - radio, y - radio, x + radio, y + radio, fill="#CAF3F1", outline="#7DF5D1", width=3)

        # Texto dentro y debajo del nodo
        self.canvas.create_text(x, y - 4, text=str(nodo.clave), font=("Arial", 10, "bold"), fill="#1A1818")
        self.canvas.create_text(x, y + 12, text=nodo.datos["nombre"][:10], font=("Arial", 8), fill="#333333")

if __name__ == "__main__":
    arbol_sistema = ArbolAdministrativo()
    root_window = tk.Tk()
    app = InterfazPruebasArbol(root_window, arbol_sistema)
    root_window.mainloop()