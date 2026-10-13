const test = require("node:test");
const assert = require("node:assert/strict");
const {parseCSV, parseUniverse, hypergeomSF, adjustBH, annotate} = require("../web/annotator.js");

test("exact upper-tail p-values", () => {
  assert.ok(Math.abs(hypergeomSF(20, 2, 2, 2) - 1 / 190) < 1e-10);
  assert.ok(Math.abs(hypergeomSF(10, 3, 2, 2) - 3 / 45) < 1e-10);
  assert.equal(hypergeomSF(10, 3, 2, 0), 1);
});
test("BH correction preserves original order", () => {
  const q = adjustBH([0.04, 0.01, 0.03]);
  q.forEach((value, i) => assert.ok(Math.abs(value - [0.04,0.03,0.04][i]) < 1e-10));
});
test("CSV quoted labels and Windows line endings", () => {
  const groups = parseCSV('cluster,gene\r\n"Cluster, 1",cd3d\r\n"Cluster, 1",CD3D\r\n', "cluster","gene");
  assert.deepEqual([...groups.get("Cluster, 1")], ["CD3D"]);
});
test("CSV rejects malformed data", () => {
  assert.throws(() => parseCSV('cluster,gene\n"bad,ABC', "cluster", "gene"), /Unterminated/);
  assert.throws(() => parseCSV("cluster,gene\nx\n", "cluster", "gene"), /field count/);
});
test("reference overlap annotates only significant clusters", () => {
  const universe = parseUniverse("G1\nG2\nG3\n" + Array.from({length:97}, (_,i)=>"R"+i).join("\n"));
  const markers = parseCSV("cluster,gene\nA,G1\nA,G2\nB,R90", "cluster", "gene");
  const refs = parseCSV("cell_type,gene\nType A,G1\nType A,G2\nType B,G3", "cell_type", "gene");
  const results = annotate(markers, refs, universe);
  assert.equal(results.find(r=>r.cluster==="A" && r.cell_type==="Type A").assignment, "Type A");
  assert.equal(results.find(r=>r.cluster==="B").assignment, "Unassigned");
});
test("genes outside universe are rejected", () => {
  assert.throws(() => annotate(new Map([["A",new Set(["ABSENT"])]]),
    new Map([["T",new Set(["G1"])]]), new Set(["G1"])), /outside the universe/);
});
test("no match with alpha = 1 is still unassigned", () => {
  const result=annotate(new Map([["A",new Set(["A"])]]),
    new Map([["T",new Set(["B"])]]),new Set(["A","B"]),1);
  assert.equal(result[0].assignment,"Unassigned");
});
