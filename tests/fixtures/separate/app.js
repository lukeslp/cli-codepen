document.getElementById('btn').addEventListener('click', () => {
  const h1 = document.querySelector('h1');
  h1.textContent = h1.textContent === 'Hello, CodePen!' ? 'Clicked!' : 'Hello, CodePen!';
});
