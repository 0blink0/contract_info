#!/usr/bin/env node
/** Stage CJS preload and static splash beside tsc output for Electron runtime. */
import { copyFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const outDir = join(root, 'dist', 'electron')

const assets = [
  { src: join(root, 'electron', 'preload.cjs'), dest: join(outDir, 'preload.cjs'), label: 'preload' },
  { src: join(root, 'electron', 'splash.html'), dest: join(outDir, 'splash.html'), label: 'splash' },
]

for (const { src, dest, label } of assets) {
  if (!existsSync(src)) {
    console.error(`Missing ${label} source: ${src}`)
    process.exit(1)
  }
  copyFileSync(src, dest)
  console.log(`Copied ${label} -> ${dest}`)
}
