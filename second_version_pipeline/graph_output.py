from langgraph.graph import StateGraph, MessagesState, START, END


def mock():
    pass
 
workflow = StateGraph(MessagesState)
workflow.add_node("Chatter", mock)
workflow.add_node("Planner", mock)
workflow.add_node("Supervisor", lambda state: {"messages": state["messages"]})
workflow.add_edge("Supervisor","Planner")
workflow.add_edge("Planner","Supervisor")
workflow.set_entry_point("Supervisor")  

graph = workflow.compile()

graph_image = graph.get_graph(xray=True).draw_mermaid_png()

with open("graph_output.png", "wb") as file:
    file.write(graph_image)