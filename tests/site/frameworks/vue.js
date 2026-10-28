import { createApp } from 'vue/dist/vue.esm-bundler.js';

createApp({
  data: () => ({ value: '', count: 0 }),
  methods: { submit() { window.__lab.state.submitted = this.value; } },
  template: `<form @submit.prevent="submit"><label for="field">Controlled value</label>
    <input id="field" v-model="value"><output id="model">{{ value }}</output>
    <button id="rerender" type="button" @click="count++">Rerender {{ count }}</button>
    <button id="submit" type="submit">Submit</button></form>`,
}).mount('#app');
