source("R/runtime.R")
tryCatch(check_readiness(), error = function(e) {
  message("ALGS Shiny readiness check failed.")
  quit(status = 1L)
})
