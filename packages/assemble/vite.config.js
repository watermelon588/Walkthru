// One ESM file for bundlers and one IIFE (`window.Assemble`) for a plain script tag.
export default {
  build: {
    lib: { entry: 'src/index.ts', name: 'Assemble', formats: ['es', 'iife'], fileName: (format) => (format === 'es' ? 'assemble.js' : 'assemble.iife.js') },
    target: 'es2022',
    sourcemap: false,
  },
}
