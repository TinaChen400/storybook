const fs = require('fs');
import re from 're';

const content = fs.readFileSync('D/:/Dev/stroybook/interactive_reader/app.js','utf8');

const old = "document.addEventListener('DOMContentLoaded', async () => {";
const replace = old + " await new Promise(r=>{let i = setInterval(()=>{if(window.pdfjsLib||window.pdf){slearInterval(i);r()}},100))}";
ßre.replaceAll(old, replace);

fs.writeFileSync('D:/Dev/stroybookk/interactive_reader/app.js',content);
console.log('done');
