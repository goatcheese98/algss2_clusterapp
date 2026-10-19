source("R/analysis.R")
p <- load_players("data/ALGS_Split_2.csv")
f <- default_filters(p)
expect_error <- function(code, message) {
  error <- tryCatch({ force(code); NULL }, error = identity)
  stopifnot(inherits(error, "error"), grepl(message, conditionMessage(error), fixed = TRUE))
}
run <- function(k = 5, per_game = FALSE, data = p, filters = f, metric = metric_choices[1]) analyze_players(data, metric, per_game, k, filters)
set.seed(42)
seed <- .Random.seed
expect_error(with_analysis_seed(stop("seed-test")), "seed-test")
stopifnot(identical(seed, .Random.seed))
first <- run()
stopifnot(identical(seed, .Random.seed), identical(first, run()), nrow(first$players) == 83)
rm(.Random.seed, envir = .GlobalEnv)
invisible(run())
stopifnot(!exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE))
stopifnot(identical(first, run()), !identical(first$players$X, run(per_game = TRUE)$players$X))
stopifnot(all(run(per_game = TRUE)$players$X == first$players$Kills / first$players$Games))
stopifnot(nrow(run(metric = metric_choices[2])$players) > 0)
# Reference the original default kmeans() call on the original filtered row order.
# Co-membership ignores cosmetic cluster-number relabeling.
for (metric in metric_choices) {
  for (per_game in if (metric == metric_choices[1]) c(FALSE, TRUE) else FALSE) {
    original <- filter_players(p, metric, f)
    fields <- if (metric == metric_choices[1]) c("Kills", "Damage_Dealt") else c("KA_D", "Damage_Difference_per_Game")
    features <- original[fields]
    if (per_game) features <- features / original$Games
    normalized <- scale(features)
    for (k in c(2, 5, 8)) {
      reference <- with_analysis_seed(kmeans(normalized, centers = k))$cluster
      actual <- run(k, metric = metric, per_game = per_game)$players
      actual <- as.integer(actual$Cluster[match(original$Player, actual$Player)])
      stopifnot(identical(unname(outer(reference, reference, "==")), unname(outer(actual, actual, "=="))))
      ranked <- order(-rowSums(normalized^2), original$Player)
      expected_labels <- match(reference, unique(reference[ranked]))
      stopifnot(identical(actual, expected_labels))
    }
  }
}
for (k in list(0, 16, 1.5, NA_real_, Inf, "3", numeric())) expect_error(run(k), "whole number")
expect_error(run(metric = "unknown"), "supported metric")
expect_error(run(per_game = NA), "true or false")
bad <- p; bad$Games[1] <- 0; expect_error(run(data = bad), "positive whole")
bad <- p; bad$Kills[1] <- Inf; expect_error(run(data = bad), "finite numeric")
bad <- p; bad$KA_D[1] <- NA; expect_error(run(data = bad), "finite numeric")
bad <- p; bad$Player[2] <- bad$Player[1]; expect_error(run(data = bad), "unique")
expect_error(run(data = p[FALSE, ]), "No players")
expect_error(run(data = p[setdiff(names(p), "Games")]), "Missing required")
f2 <- f; f2$kills <- c(10000, 10001); expect_error(run(filters = f2), "No players")
f2$kills <- c(20, 1); expect_error(run(filters = f2), "ordered finite")
f2$kills <- c(NA, 1); expect_error(run(filters = f2), "ordered finite")
small <- p[1:3, ]; small$Kills <- 1; small$Damage_Dealt <- 2
fs <- default_filters(small, TRUE)
expect_error(run(2, data = small, filters = fs), "valid distinct rows (1)")
stopifnot(nrow(run(1, data = small, filters = fs)$players) == 3)
small$Kills <- 1:3
fs <- default_filters(small, TRUE)
stopifnot(nlevels(run(3, data = small, filters = fs)$players$Cluster) == 3)
# k equal to distinct rows with duplicates still uses the original defaults.
small <- p[1:3, ]; small$Kills <- c(1, 1, 2); small$Damage_Dealt <- c(2, 2, 3)
fs <- default_filters(small, TRUE)
reference <- with_analysis_seed(kmeans(scale(small[c("Kills", "Damage_Dealt")]), centers = 2))$cluster
actual <- as.integer(run(2, data = small, filters = fs)$players$Cluster)
stopifnot(identical(unname(outer(reference, reference, "==")), unname(outer(actual, actual, "=="))))
expect_error(load_players(textConnection("wrong,header\n1,2")), "schema")
one <- p[1, ]; stopifnot(nrow(run(1, data = one, filters = default_filters(one, TRUE))$players) == 1)
cat("Analysis tests passed\n")
