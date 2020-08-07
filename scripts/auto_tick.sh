# This script will:

# 1. pull all feedstocks from GitHub
# 2. create a dependency graph of feedstocks
# 3. update version numbers in the dependency graph
# 4. create migrations and not run them
# 5. run migrations and submit pull requests on GitHub for the nsls-ii-forge
# 5. display the status of migrations/pull requests

# This will use ~/.conda-smithy authentication for GitHub token
# It will use nsls2forge username on GitHub
# It will not fork repositories but instead create new branches
# It will use a max of 10 workers to build the graph

# If something goes wrong while executing this script
# please use 'auto-tick clean', fix the issue, and try again


# get all feedstock names and write them to names.txt
all-feedstocks list -u $GITHUB_USERNAME -t $GITHUB_TOKEN -o nsls-ii-forge -w
# create graph with node_attrs/* and graph.json
graph-utils make -o nsls-ii-forge -c -f names.txt -m 10
# update graph with new versions from their sources (see versions/*)
graph-utils update
# dry run of migrations to catch errors before PRs
auto-tick run --dry-run
# full run of migrations and submit PRs (see pr_json/*)
auto-tick run
# output status of migrations to status/*
auto-tick status