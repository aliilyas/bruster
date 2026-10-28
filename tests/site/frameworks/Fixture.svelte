<script>
  let value = '';
  let count = 0;
  function submit(event) {
    event.preventDefault();
    window.__lab.state.submitted = value;
  }
</script>

<form onsubmit={submit}>
  <label for="field">Controlled value</label>
  <input id="field" bind:value>
  <output id="model">{value}</output>
  <button id="rerender" type="button" onclick={() => count++}>Rerender {count}</button>
  <button id="submit" type="submit">Submit</button>
</form>
