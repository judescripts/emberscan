export const THEME_KEY = "es-theme";

/** Runs before first paint (in <head>) so a saved dark theme doesn't flash light. */
export const THEME_SCRIPT = `try{var t=localStorage.getItem("${THEME_KEY}");if(t==="dark")document.documentElement.dataset.theme="dark"}catch(e){}`;
