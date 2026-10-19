source("scripts/dependencies.R")
check_dependencies()
library(shiny)
source("R/analysis.R")
players <- load_players("data/ALGS_Split_2.csv")
defaults <- default_filters(players)
range_slider <- function(id, label, values, step = 1) {
  sliderInput(id, label, min = min(values), max = max(values), value = defaults[[id]], step = step, width = "100%")
}
ui <- fluidPage(
  tags$head(tags$title("ALGS · Player analysis"),
    tags$link(rel = "stylesheet", href = "lum.css"),
    tags$script(src = "busy.js", defer = NA)),
  tags$a(href = "#results", class = "skip-link", "Skip to results"),
  tags$header(tags$div(class = "topline", tags$strong("ALGS · Player analysis"), tags$a(href = "#methodology", "Methodology")),
    tags$h1("Find patterns in player performance."),
    tags$p("Explore standardized features. Clusters describe similarity, not player quality.")),
  tags$div(class = "workspace",
    tags$aside(id = "setup", `aria-label` = "Clustering setup",
      tags$h2("Clustering setup"),
      selectInput("plot_choice", "Compare metrics", choices = metric_choices, selectize = FALSE),
      checkboxInput("per_game", "Cluster on per-game metrics", FALSE),
      numericInput("clusters", "Number of clusters", value = 5, min = 1, max = 15, step = 1),
      tags$p(class = "muted", "Standardized features · fixed seed"),
      conditionalPanel("input.plot_choice === 'Kills vs Damage Dealt'",
        range_slider("games", "Games played", players$Games),
        range_slider("kills", "Kills", c(1, players$Kills)),
        range_slider("damage_dealt", "Damage dealt", c(0, players$Damage_Dealt))),
      conditionalPanel("input.plot_choice !== 'Kills vs Damage Dealt'",
        range_slider("ka_d", "K+A/D", c(0, players$KA_D), .01),
        range_slider("damage_diff", "Damage difference per game", players$Damage_Difference_per_Game)),
      actionButton("run", "Run analysis", class = "primary"),
      actionButton("reset", "Reset example"), actionButton("clear", "Clear filters")),
    tags$main(id = "results", tabindex = "-1", `aria-label` = "Analysis results",
      tags$a(class = "edit-link", href = "#setup", "Edit analysis"),
      tags$div(role = "status", `aria-live` = "polite", textOutput("status")),
      tags$div(style = "display:none", textOutput("ready")),
      conditionalPanel("output.ready === 'true'",
      tabsetPanel(id = "view", tabPanel("Chart", value = "chart",
        tags$h2("Performance map"),
        tags$p("Each shape and color identifies a cluster. The table and player selector provide a keyboard alternative."),
        plotly::plotlyOutput("clusterPlot", height = "420px")),
        tabPanel("Table", value = "table", tags$h2("Player statistics"),
          selectInput("selected_cluster", "Selected cluster for tabulation", "All", selectize = FALSE),
          tags$div(class = "table-region", role = "region", `aria-label` = "Scrollable player statistics", tabindex = "0", DT::DTOutput("playerTable")))),
      selectInput("player", "Inspect player", choices = character(), selectize = FALSE),
      tags$section(tabindex = "0", `aria-label` = "Selected player details", `aria-live` = "polite", uiOutput("detail"))),
      tags$section(id = "methodology", tags$h2("Methodology"),
        tags$p("ALGS Year 4 Split 2 Playoffs · Data source: Liquipedia. K-means uses standardized selected metrics, the original one-start defaults and a fixed seed. Per-game mode divides kills and damage by games before clustering; K+A/D and damage difference per game are already rates. Raw filters remain on totals."),
        tags$p("Cluster numbers are labels, not rankings. Change filters, then run analysis. Reset restores the original example; Clear filters includes the full dataset.")))
  )
)
server <- function(input, output, session) {
  analysis <- reactiveVal(NULL)
  status <- reactiveVal("Choose filters, then Run analysis.")
  current <- reactiveVal(FALSE)
  filters <- reactive(list(games = input$games, kills = input$kills,
    damage_dealt = input$damage_dealt, ka_d = input$ka_d, damage_diff = input$damage_diff))
  observeEvent(list(input$plot_choice, input$per_game, input$clusters, filters()), {
    current(FALSE)
    status("Settings changed. Run analysis to view current results.")
  }, ignoreInit = TRUE, priority = 10)
  observeEvent(input$run, {
    current(FALSE)
    analysis(NULL)
    status("Running analysis…")
    result <- tryCatch(analyze_players(players, input$plot_choice, input$per_game, input$clusters, filters()), error = identity)
    if (inherits(result, "error")) {
      status(paste(conditionMessage(result), "Adjust settings or Clear filters, then Run analysis to retry."))
      updateSelectInput(session, "player", choices = character())
      return()
    }
    analysis(result)
    current(TRUE)
    status(sprintf("%d players · %d clusters. Analysis complete.", nrow(result$players), result$clusters))
    updateSelectInput(session, "selected_cluster", choices = c("All", levels(result$players$Cluster)), selected = "All")
    updateSelectInput(session, "player", choices = result$players$Player, selected = result$players$Player[1])
  })
  reset_filters <- function(clear) {
    values <- default_filters(players, clear)
    for (id in names(values)) updateSliderInput(session, id, value = values[[id]])
    if (!clear) {
      updateSelectInput(session, "plot_choice", selected = metric_choices[1])
      updateCheckboxInput(session, "per_game", value = FALSE)
      updateNumericInput(session, "clusters", value = 5)
    }
    current(FALSE)
    status("Filters updated. Run analysis to view results.")
  }
  observeEvent(input$reset, reset_filters(FALSE))
  observeEvent(input$clear, reset_filters(TRUE))
  output$status <- renderText(status())
  output$ready <- renderText(if (current()) "true" else "false")
  outputOptions(output, "ready", suspendWhenHidden = FALSE)
  visible_result <- reactive({
    validate(need(current(), "Run analysis to view current results."))
    req(analysis())
    analysis()
  })
  output$clusterPlot <- plotly::renderPlotly({
    result <- visible_result()
    d <- result$players
    # Shapes distinguish clusters beyond color; black/white outlines aid contrast.
    colors <- c("#2874b8", "#b45417", "#16845d", "#a74c9f", "#a84142")
    p <- plotly::plot_ly(d, x = ~X, y = ~Y, color = ~Cluster,
      colors = rep(colors, length.out = result$clusters), symbol = ~Cluster,
      symbols = c("circle", "diamond", "square", "cross", "triangle-up", "triangle-down", "x", "star", "hexagon", "pentagon", "hourglass", "bowtie", "triangle-left", "triangle-right", "diamond-open"),
      text = ~paste(Player, "· Cluster", Cluster), hoverinfo = "text+x+y",
      type = "scatter", mode = "markers", marker = list(size = 10, line = list(color = "#888888", width = 1)))
    plotly::config(plotly::layout(p, xaxis = list(title = result$labels[1], automargin = TRUE),
      yaxis = list(title = result$labels[2], automargin = TRUE),
      font = list(family = "Geist, sans-serif", size = 13, color = "#66666f"),
      paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
      legend = list(orientation = "h", y = -.3), margin = list(l = 65, r = 16, t = 16, b = 100)),
      displayModeBar = FALSE, responsive = TRUE)
  })
  table_data <- reactive({
    d <- visible_result()$players
    if (!is.null(input$selected_cluster) && input$selected_cluster != "All") d <- d[as.character(d$Cluster) == input$selected_cluster, , drop = FALSE]
    d[c("Player", "Cluster", "Games", "X", "Y", "Kills", "Assists", "Knocks", "Damage_Dealt", "Damage_Taken", "Damage_Difference", "Damage_Difference_per_Game", "K_D", "KA_D")]
  })
  output$playerTable <- DT::renderDT({
    d <- table_data()
    labels <- names(d)
    labels[match(c("X", "Y"), labels)] <- visible_result()$labels
    DT::datatable(d, colnames = gsub("_", " ", labels), rownames = FALSE, extensions = "Buttons", selection = "single",
      options = list(pageLength = 10, lengthMenu = c(10, 25, 50), scrollX = TRUE,
        dom = "Blfrtip", buttons = c("copy", "csv", "excel", "pdf", "print")))
  }, server = FALSE)
  observeEvent(input$playerTable_rows_selected, {
    row <- input$playerTable_rows_selected
    d <- table_data()
    if (length(row) == 1 && row >= 1 && row <= nrow(d)) updateSelectInput(session, "player", selected = d$Player[row])
  })
  output$detail <- renderUI({
    result <- visible_result()
    req(input$player)
    row <- result$players[result$players$Player == input$player, , drop = FALSE]
    req(nrow(row) == 1)
    tags$div(tags$h2(row$Player), tags$p(paste("Cluster", row$Cluster, "·", row$Games, "games")),
      tags$dl(tags$dt(result$labels[1]), tags$dd(round(row$X, 2)), tags$dt(result$labels[2]), tags$dd(round(row$Y, 2))))
  })
}
shinyApp(ui, server)
