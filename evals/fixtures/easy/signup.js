document.getElementById('signup').addEventListener('submit', function (event) {
  event.preventDefault();
  const email = this.email.value.trim();
  const password = this.password.value;
  const error = document.getElementById('error');
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    error.textContent = 'Enter a valid email address.';
    error.hidden = false;
    return;
  }
  if (password.length < 8) {
    error.textContent = 'Password must be at least 8 characters.';
    error.hidden = false;
    return;
  }
  location.href = '/welcome.html';
});
