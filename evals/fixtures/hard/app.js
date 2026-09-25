/* Zentrix front-end bundle (fixture). X4: live-looking secrets shipped to the client.
   Placeholders are filled in by serve.py so the literal patterns never sit in git (GitHub push protection). */
var STRIPE_SECRET = "__STRIPE_LIVE_KEY__";
var AWS_KEY = "__AWS_ACCESS_KEY__";
var SENDGRID_KEY = "__SENDGRID_KEY__";  /* X14: a second provider's key, found by the gitleaks rule set */
function openModal() { document.getElementById('modal').hidden = false; }
function closeModal() { document.getElementById('modal').hidden = true; }
//# sourceMappingURL=app.js.map
