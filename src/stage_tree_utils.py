# -*- coding: utf-8 -*-
from graph_tool.draw import graphviz_draw

def pretty_stage(stage):
    return str(stage)

def export(tree, filename, struct_only=False):
    SIZE = (200, 150)
    FONT_SIZE = 40.0
    
    labels = tree.graph.new_vertex_property("string")
    colors = tree.graph.new_vertex_property("string")
    
    for i in tree.stages:
        labels[i] = pretty_stage(tree.stages[i])
        colors[i] = "gold"         if (i in tree.failed_stages) else \
                    "darkorchid1"  if (i in tree.failed_witness_stages) else \
                    "deepskyblue1" if (i in tree.true_stages)   else \
                    "firebrick2"   if (i in tree.false_stages)  else "azure2"

    if not struct_only:
        graphviz_draw(tree.graph, layout="dot",
                      vprops={"label": labels, "fillcolor": colors,
                              "fontsize": FONT_SIZE},
                      output=filename, size=SIZE, ratio="auto")
    else:
        graphviz_draw(tree.graph, layout="dot",
                      vprops={"fillcolor": colors},
                      output=filename, size=SIZE, ratio="auto")
