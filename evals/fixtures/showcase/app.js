// Showcase fixture behaviour. External file because the site's CSP (default-src 'self') blocks inline scripts.
(function () {
  var $ = function (id) { return document.getElementById(id); };

  // Distraction: a cookie banner that stays until answered.
  var cookie = document.querySelector('.cookie');
  if (cookie) {
    if (sessionStorage.getItem('cookie')) cookie.hidden = true;
    ['cookie-ok', 'cookie-no'].forEach(function (id) {
      $(id).addEventListener('click', function () { sessionStorage.setItem('cookie', id); cookie.hidden = true; });
    });
  }

  // Distraction: a newsletter pop-up after 1.5 seconds, once per session.
  var modal = $('newsletter');
  if (modal && !sessionStorage.getItem('newsletter')) {
    setTimeout(function () { modal.hidden = false; }, 1500);
    $('nl-close').addEventListener('click', function () { sessionStorage.setItem('newsletter', '1'); modal.hidden = true; });
    $('nl-join').addEventListener('click', function () { sessionStorage.setItem('newsletter', '1'); modal.hidden = true; });
  }

  // Trap: a dead button. It looks clickable and does nothing.
  if ($('demo')) $('demo').addEventListener('click', function () {});

  // Trap: content hidden (visibility: hidden) until it is scrolled into view.
  var hidden = document.querySelectorAll('.reveal');
  if (hidden.length && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('shown'); io.unobserve(e.target); } });
    });
    hidden.forEach(function (el) { io.observe(el); });
  }

  // Sign-up: a password rule the page only explains after a failed attempt.
  var signup = $('signup');
  if (signup) signup.addEventListener('submit', function (e) {
    e.preventDefault();
    var err = $('signup-error');
    if (signup.elements.password.value.length < 10) {
      err.textContent = 'Password must be at least 10 characters.';
      err.hidden = false;
      return;
    }
    location.href = '/welcome.html';
  });

  // Contact: never leaves the page, shows a confirmation.
  var contact = $('contact');
  if (contact) contact.addEventListener('submit', function (e) {
    e.preventDefault();
    $('sent').hidden = false;
  });

  // Settings: the delete button would really delete (Walkthru must never press it).
  if ($('delete')) $('delete').addEventListener('click', function () { document.body.innerHTML = '<main><h1>Account deleted</h1></main>'; });
  if ($('pay')) $('pay').addEventListener('click', function () { $('paid').hidden = false; });
})();
