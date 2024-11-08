import sys
import pandas as pd
import numpy as np
import networkx as nx
from PyQt5 import QtWidgets
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from tqdm import tqdm  # Import tqdm for progress bar

# Load data
print("Loading data...")
articles_df = pd.read_json("test_processed_article_stats_data.json")
print("Data loaded.")


class CollaborationNetworkApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Collaboration Network")
        self.setGeometry(100, 100, 800, 600)

        # Create a graph
        self.graph = nx.Graph()
        self.edge_info = {}

        print("Building graph...")
        # Build the graph and collect edge information
        for article, details in articles_df["math"]["article_citation_map"].items():
            authors = details["faculty_members"]
            for i in range(len(authors)):
                for j in range(i + 1, len(authors)):
                    edge = tuple(sorted((authors[i], authors[j])))
                    self.graph.add_edge(*edge)
                    if edge not in self.edge_info:
                        self.edge_info[edge] = []
                    self.edge_info[edge].append(article)
        print(
            "Graph built with",
            len(self.graph.nodes),
            "nodes and",
            len(self.graph.edges),
            "edges.",
        )

        # Create a plot widget
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)

        # Draw the network
        self.draw_network()

        # Connect mouse press event
        self.plot_widget.scene().sigMouseClicked.connect(self.on_mouse_click)

    def draw_network(self):
        print("Calculating layout...")
        pos = nx.spring_layout(self.graph, k=0.15, iterations=20)
        self.node_positions = pos
        print("Layout calculated.")

        # Draw edges with progress bar
        print("Drawing edges...")
        total_edges = len(self.graph.edges())
        with tqdm(total=total_edges, desc="Drawing edges", unit="edge") as pbar:
            for idx, edge in enumerate(self.graph.edges(), start=1):
                tqdm.write(f"Drawing edge between {edge[0]} and {edge[1]}")
                x0, y0 = pos[edge[0]]
                tqdm.write(f"x0: {x0}, y0: {y0}")
                x1, y1 = pos[edge[1]]
                tqdm.write(f"x1: {x1}, y1: {y1}")
                line = pg.PlotDataItem(
                    [x0, x1], [y0, y1], pen=pg.mkPen("gray", width=1)
                )
                tqdm.write(f"Line: {line}")
                tqdm.write(f"Adding line to plot widget")
                self.plot_widget.addItem(line)
                tqdm.write(f"Line added to plot widget")
                remaining_items = total_edges - idx
                completion_percentage = (idx / total_edges) * 100
                tqdm.write(
                    f"Remaining items: {remaining_items}, Completion: {completion_percentage:.2f}%"
                )
                tqdm.write(f"now doing the next edge")
                pbar.update(1)  # Update the progress bar
        print("Edges drawn.")

        # Draw nodes
        print("Drawing nodes...")
        self.node_items = {}
        for node, (x, y) in pos.items():
            node_item = pg.ScatterPlotItem(
                [x], [y], size=10, brush=pg.mkBrush(255, 0, 0, 120)
            )
            self.plot_widget.addItem(node_item)
            self.node_items[node] = node_item
        print("Nodes drawn.")

    def on_mouse_click(self, event):
        pos = event.scenePos()
        mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
        x, y = mouse_point.x(), mouse_point.y()

        # Check if a node is clicked
        for node, node_item in self.node_items.items():
            node_pos = self.node_positions[node]
            if (
                np.linalg.norm(np.array([x, y]) - np.array(node_pos)) < 0.1
            ):  # Simple proximity check
                self.show_node_info(node)
                return

        # Check if an edge is clicked
        for edge in self.graph.edges():
            x0, y0 = self.node_positions[edge[0]]
            x1, y1 = self.node_positions[edge[1]]
            if self.is_point_near_line(x, y, x0, y0, x1, y1):
                self.show_edge_info(edge)
                return

    def is_point_near_line(self, px, py, x0, y0, x1, y1, tol=0.05):
        # Check if point (px, py) is near the line segment (x0, y0) to (x1, y1)
        line_vec = np.array([x1 - x0, y1 - y0])
        point_vec = np.array([px - x0, py - y0])
        line_len = np.linalg.norm(line_vec)
        if line_len < 1e-5:
            return False
        line_unitvec = line_vec / line_len
        proj_length = np.dot(point_vec, line_unitvec)
        if proj_length < 0 or proj_length > line_len:
            return False
        nearest_point = np.array([x0, y0]) + proj_length * line_unitvec
        dist = np.linalg.norm(np.array([px, py]) - nearest_point)
        return dist < tol

    def show_node_info(self, node):
        QtWidgets.QMessageBox.information(
            self,
            "Node Info",
            f"Node: {node}\nCollaborations: {self.graph.degree[node]}",
        )

    def show_edge_info(self, edge):
        articles = ", ".join(self.edge_info[edge])
        QtWidgets.QMessageBox.information(
            self,
            "Edge Info",
            f"Collaboration between {edge[0]} and {edge[1]}\nArticles: {articles}",
        )


def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = CollaborationNetworkApp()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
