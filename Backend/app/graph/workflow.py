"""LangGraph fan-out / join workflow; no external LangGraph service required."""
from functools import partial
from langgraph.graph import StateGraph, START, END
from .state import PlanningState
from . import nodes

def build_workflow(specialist, planner):
    graph = StateGraph(PlanningState)
    graph.add_node('prepare', nodes.prepare)
    graph.add_node('places', partial(nodes.places, specialist=specialist))
    graph.add_node('weather', partial(nodes.weather, specialist=specialist))
    graph.add_node('synthesize', partial(nodes.synthesize, planner=planner))
    graph.add_node('validate', nodes.validate)
    graph.add_edge(START, 'prepare')
    graph.add_edge('prepare', 'places')
    graph.add_edge('prepare', 'weather')
    graph.add_edge(['places', 'weather'], 'synthesize')
    graph.add_edge('synthesize', 'validate')
    graph.add_edge('validate', END)
    return graph.compile()
