const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('studio.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
new vm.Script(script);
for(const id of ['secretBar','heading','detail','studioBar'])assert(html.includes(`id="${id}"`),`Missing UI target: ${id}`);
assert(script.includes("mode==='secrets'"));
assert(script.includes("op:'secret-list'"));
console.log('JavaScript and Secret Manager routing checks passed.');
