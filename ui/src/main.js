// import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { OhVueIcon, addIcons } from "oh-vue-icons";

import App from './App.vue'
import router from './router'

import Buefy from 'buefy'
import 'buefy/dist/buefy.css'
import llmmConfig from './configuration/backend';

import * as FaIcons from "oh-vue-icons/icons/fa";

const Fa = Object.values({ ...FaIcons });
addIcons(...Fa);

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Buefy)
app.use(llmmConfig)
app.component("v-icon", OhVueIcon);

app.mount('#app')
