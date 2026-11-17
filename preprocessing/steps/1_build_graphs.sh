#!/usr/bin/env bash
# Step 1: build the graphs.
# Joern parses every C/C++ file into a graph database and Neo4j serves it. The paper's scripts then build the
# control-flow graph and the program dependence graph (PDG) of each function, plus the call graph.
source /preprocessing/lib.sh
echo "STEP 1  Build graphs"
cd "$W"; rm -rf .joernIndex
stage joern_parse java -jar /opt/joern/bin/joern.jar src
neo4j_up
rm -rf "$S2S"; cp -r /opt/sysevr/Implementation/source2slice "$S2S"; cd "$S2S"
mkdir -p cfg_db pdg_db dict_call2cfgNodeID_funcID C/test_data/4
for s in get_cfg_relation complete_PDG access_db_operate; do stage "$s" "$PY27" "$s.py"; done
echo "   programs: $(ls "$W/src" | wc -l), PDG files: $(find pdg_db -type f | wc -l)"
