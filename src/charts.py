import plotly.express as px

def build_plot(plot_info, data, columns):
    if plot_info["tipo"] == "none":
        return None

    else:
        try:
            tags_col = columns.index(plot_info["etiquetas"])
            tags = [row[tags_col] for row in data]

            data_col = columns.index(plot_info["valores"])
            tag_values = [abs(row[data_col]) for row in data]

        except (ValueError, TypeError):
            return None

        if plot_info["tipo"] == "pie":
            fig = px.pie(names = tags, values = tag_values, title = plot_info["titulo"])

        elif plot_info["tipo"] == "bar":
            fig = px.bar(x = tags, y = tag_values, title = plot_info["titulo"])

        elif plot_info["tipo"] == "line":
            fig = px.line(x = tags, y = tag_values, title = plot_info["titulo"])
        
        else:
            return None

    return fig