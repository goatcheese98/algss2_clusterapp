# Pure analysis boundary. No network or package installation occurs here.
metric_choices <- c("Kills vs Damage Dealt", "K+A/D vs Damage Difference per Game")
source_names <- c("Player", " Games", "/dgs/assets/icons/kills.svg Kills",
  "/dgs/assets/icons/assists.svg Assists", "/dgs/assets/icons/knockdown.svg Knocks",
  "/dgs/assets/icons/damage.svg Dmg dealt", "/dgs/assets/icons/damage.svg Dmg taken",
  "/dgs/assets/icons/damage.svg Dmg diff", "/dgs/assets/icons/ring.svg Ring dmg",
  "/dgs/assets/icons/revives.svg Rez.", "/dgs/assets/icons/revives.svg Rspn.",
  "K/D", "KA/D", "Surv. time")
column_names <- c("Player", "Games", "Kills", "Assists", "Knocks", "Damage_Dealt",
  "Damage_Taken", "Damage_Difference", "Ring_Damage", "Revives", "Respawns",
  "K_D", "KA_D", "Survival_Time")
load_players <- function(path) {
  players <- read.csv(path, check.names = FALSE, stringsAsFactors = FALSE)
  if (!identical(names(players), source_names)) stop("ALGS data schema does not match the expected 14 columns.")
  names(players) <- column_names
  validate_players(players)
  players$Damage_Difference_per_Game <- round(players$Damage_Difference / players$Games, 2)
  players
}
validate_players <- function(players) {
  if (!is.data.frame(players) || !all(column_names %in% names(players))) stop("Missing required player columns.")
  if (!nrow(players)) stop("No players match these filters")
  if (anyNA(players$Player) || any(!nzchar(trimws(players$Player))) || anyDuplicated(players$Player)) stop("Player names must be present and unique.")
  for (name in column_names[2:13]) {
    if (!is.numeric(players[[name]]) || any(!is.finite(players[[name]]))) stop(paste(name, "must contain finite numeric values."))
  }
  if (any(players$Games <= 0 | players$Games != floor(players$Games))) stop("Games must be positive whole numbers.")
  invisible(TRUE)
}
validate_range <- function(value, name) {
  if (!is.numeric(value) || length(value) != 2L || any(!is.finite(value)) || value[1] > value[2]) stop(paste(name, "requires an ordered finite minimum and maximum."))
}
default_filters <- function(players, clear = FALSE) {
  list(games = c(if (clear) min(players$Games) else 24, max(players$Games)),
    kills = c(if (clear) min(players$Kills) else 20, max(players$Kills)),
    damage_dealt = c(0, max(players$Damage_Dealt)),
    ka_d = c(if (clear) min(players$KA_D) else 2, max(players$KA_D)),
    damage_diff = c(if (clear) min(players$Damage_Difference_per_Game) else 0,
      max(players$Damage_Difference_per_Game)))
}
filter_players <- function(players, metric, filters) {
  validate_players(players)
  if (!is.character(metric) || length(metric) != 1L || !metric %in% metric_choices) stop("Choose one of the two supported metric comparisons.")
  fields <- if (metric == metric_choices[1]) c(games = "Games", kills = "Kills", damage_dealt = "Damage_Dealt") else c(ka_d = "KA_D", damage_diff = "Damage_Difference_per_Game")
  keep <- rep(TRUE, nrow(players))
  for (key in names(fields)) {
    validate_range(filters[[key]], key)
    values <- players[[fields[[key]]]]
    keep <- keep & values >= filters[[key]][1] & values <= filters[[key]][2]
  }
  players[keep, , drop = FALSE]
}
with_analysis_seed <- function(code) {
  present <- exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
  if (present) previous <- get(".Random.seed", envir = .GlobalEnv)
  kind <- RNGkind()
  on.exit({
    do.call(RNGkind, as.list(kind))
    if (present) assign(".Random.seed", previous, envir = .GlobalEnv)
    else if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) rm(".Random.seed", envir = .GlobalEnv)
  })
  set.seed(20261019, kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection")
  force(code)
}
analyze_players <- function(players, metric, per_game, clusters, filters) {
  if (!is.logical(per_game) || length(per_game) != 1L || is.na(per_game)) stop("Per-game mode must be true or false.")
  if (!is.numeric(clusters) || length(clusters) != 1L || !is.finite(clusters) || clusters != floor(clusters) || clusters < 1 || clusters > 15) stop("Clusters must be a whole number from 1 to 15.")
  result <- filter_players(players, metric, filters)
  validate_players(result)
  result <- result[order(result$Player), , drop = FALSE]
  if (metric == metric_choices[1]) {
    result$X <- result$Kills / if (per_game) result$Games else 1
    result$Y <- result$Damage_Dealt / if (per_game) result$Games else 1
    labels <- c("Kills", "Damage dealt")
    if (per_game) labels <- paste(labels, "per game")
  } else {
    result$X <- result$KA_D
    result$Y <- result$Damage_Difference_per_Game
    labels <- c("K+A/D", "Damage difference per game")
  }
  features <- as.matrix(result[c("X", "Y")])
  if (any(!is.finite(features))) stop("Selected metrics must contain finite values.")
  distinct <- nrow(unique(features))
  if (clusters > distinct) stop(sprintf("Clusters (%d) must not exceed valid distinct rows (%d).", clusters, distinct))
  # Constant features contribute zero distance, avoiding NaN from scale().
  spread <- apply(features, 2, sd)
  spread[!is.finite(spread) | spread == 0] <- 1
  normalized <- sweep(sweep(features, 2, colMeans(features)), 2, spread, "/")
  if (any(!is.finite(normalized))) stop("Selected metrics cannot be standardized to finite values.")
  # Lloyd supports k equal to the row count; Hartigan-Wong rejects that boundary.
  km <- with_analysis_seed(kmeans(normalized, centers = clusters, nstart = 20, algorithm = "Lloyd", iter.max = 100))
  # Keep the original distance-based relabeling, with deterministic row tie breaks.
  ranked <- order(-rowSums(normalized^2), result$Player)
  levels <- unique(km$cluster[ranked])
  result$Cluster <- factor(match(km$cluster, levels), levels = seq_len(clusters))
  list(players = result, labels = labels, metric = metric, per_game = per_game, clusters = clusters)
}
