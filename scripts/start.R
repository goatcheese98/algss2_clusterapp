source("R/runtime.R")
port <- runtime_port()
check_runtime()
# Shiny's runApp reads app.R and its data before serving requests.
# The container init forwards stop signals to R and reaps child processes.
options(shiny.sanitize.errors = TRUE)
shiny::runApp(".", host = "0.0.0.0", port = port, launch.browser = FALSE)
