import plotly.express as px

def build_plot(plot_info, data, columns):
    plot_type = plot_info.get("tipo")
    if plot_type == "none" or not data:
        return None

    else:
        try:
            tags_col = columns.index(plot_info["etiquetas"])
            tags = [row[tags_col] for row in data]

            data_col = columns.index(plot_info["valores"])
            tag_values = [abs(row[data_col]) for row in data]

            plot_title = plot_info["titulo"]
            plot_x = plot_info["etiquetas"]
            plot_y = plot_info["valores"]

        except (ValueError, TypeError, KeyError):
            return None

        if plot_type == "pie":
            fig = px.pie(names=tags, values=tag_values, title=plot_title)

        elif plot_type == "bar":
            fig = px.bar(x=tags, y=tag_values, title=plot_title, labels={"x": plot_x, "y": plot_y})

        elif plot_type == "line":
            fig = px.line(x=tags, y=tag_values, title=plot_title, labels={"x": plot_x, "y": plot_y})
        
        else:
            return None

    fig.update_layout(modebar_remove=["zoom", "pan", "select", "lasso", "zoomin", "zoomout", "autoscale", "resetScale"],
                      template="plotly_dark", height=340, width=750,)
    return fig