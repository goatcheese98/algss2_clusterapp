# Explicit setup; never sourced by the app. Requires R 4.5.0 and build tools.
source("scripts/dependencies.R")
versions <- dget("scripts/package-versions.R")
lib <- Sys.getenv("R_LIBS_USER", unset = "")
if (!nzchar(lib)) stop("Set R_LIBS_USER to a writable library before setup.")
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
# The manifest is in dependency order; all transitive CRAN versions are pinned.
installed_version <- function(pkg) tryCatch(packageVersion(pkg), error = function(e) NULL)
for (pkg in names(versions)) {
  if (!is.null(installed_version(pkg)) && installed_version(pkg) == numeric_version(versions[[pkg]])) next
  filename <- sprintf("%s_%s.tar.gz", pkg, versions[[pkg]])
  archive <- sprintf("https://cran.r-project.org/src/contrib/Archive/%s/%s", pkg, filename)
  current <- paste0("https://cran.r-project.org/src/contrib/", filename)
  dest <- file.path(tempdir(), filename)
  fetched <- FALSE
  for (url in c(archive, current)) {
    fetched <- tryCatch({ download.file(url, dest, mode = "wb", quiet = TRUE); TRUE }, error = function(e) FALSE)
    if (fetched) break
  }
  if (!fetched) stop(paste("Unable to fetch pinned source:", filename))
  install.packages(dest, repos = NULL, type = "source", lib = lib)
  if (is.null(installed_version(pkg)) || installed_version(pkg) != numeric_version(versions[[pkg]])) stop(paste("Pinned installation failed:", pkg))
}
check_dependencies()
