# Explicit setup only. Never sourced by the running app.
dependencies <- c(shiny = "1.10.0", ggplot2 = "3.5.1", plotly = "4.10.4", DT = "0.33")
check_dependencies <- function() {
  problems <- names(dependencies)[!vapply(names(dependencies), function(pkg) {
    requireNamespace(pkg, quietly = TRUE) && as.character(utils::packageVersion(pkg)) == dependencies[[pkg]]
  }, logical(1))]
  if (length(problems)) stop(paste("Install the pinned dependencies first; see README. Mismatch:", paste(problems, collapse = ", ")))
  invisible(TRUE)
}
