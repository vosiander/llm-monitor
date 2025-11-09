import axios from "axios";

const llmmonitor = {
  url: import.meta.env.VITE_LLMMONITOR_URL,
  axios: axios.create({
      baseURL: import.meta.env.VITE_LLMMONITOR_URL,
      timeout: 10000,
      params: {} // do not remove this, its added to add params later in the config
  })
}

export default {
  install(app) {
    app.provide('llmmonitor', llmmonitor);

    // llmmonitor.axios.interceptors.request.use(function (config) {
    //    config.headers.TEST = "TRUE"
    //     const keycloak = app.config.globalProperties.$keycloak;
    //     console.log("---------------")
    //     console.log(keycloak)
    //     if (keycloak.authenticated) {
    //       console.log(config)
    //       config.headers.Authorization = `Bearer ${keycloak.idToken}`
    //     }
    //     return config
    //
    //   }, error => {
    //     return Promise.reject(error)
    //   })

    // Example: Adding a global method
    // app.config.globalProperties.$getBackendData = async () => {
    //   const response = await fetch(options.backendUrl);
    //   return await response.json();
    // };

    console.log('Backend config plugin installed.');
  }
};
