# vapi-web.js
Bundle del SDK `@vapi-ai/web` **3.0.0** (da npm, pacchetto ufficiale Vapi), minificato in un unico file.
Si carica **solo** quando il visitatore tocca "Voce naturale" e Vapi è configurato (chiavi in Admin › Impostazioni).
Il SDK carica poi a runtime il componente di chiamata di Daily (`@daily-co/daily-js`) dai server Daily.
Ricostruire: `npm i @vapi-ai/web@3.0.0 esbuild` e `npx esbuild entry.js --bundle --minify --format=iife --target=es2019 --outfile=vapi-web.js`
con `entry.js` = `import Vapi from "@vapi-ai/web"; window.VapiWeb = Vapi.default || Vapi;`
