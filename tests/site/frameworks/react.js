import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';

function Fixture() {
  const [value, setValue] = useState('');
  const [count, setCount] = useState(0);
  return React.createElement('form', {
    onSubmit(event) { event.preventDefault(); window.__lab.state.submitted = value; },
  },
  React.createElement('label', { htmlFor: 'field' }, 'Controlled value'),
  React.createElement('input', { id: 'field', value, onChange: event => setValue(event.target.value) }),
  React.createElement('output', { id: 'model' }, value),
  React.createElement('button', { id: 'rerender', type: 'button', onClick: () => setCount(count + 1) }, `Rerender ${count}`),
  React.createElement('button', { id: 'submit', type: 'submit' }, 'Submit'));
}
createRoot(document.getElementById('app')).render(React.createElement(Fixture));
