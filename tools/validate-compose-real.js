// Compose validation using a real YAML parser (js-yaml) plus structural checks.
//
// Run with:  node tools/validate-compose-real.js
// Requires js-yaml to be resolvable. If it is not installed in the project, the
// caller passes NODE_PATH pointing at a temporary install, so nothing is added
// to the project's own dependencies.
'use strict'

const fs = require('fs')
const path = require('path')
const yaml = require('js-yaml')

const root = path.resolve(__dirname, '..')
const composePath = path.join(root, 'docker-compose.yml')
const errors = []
const notes = []
const rel = (p) => path.relative(root, p).replace(/\\/g, '/')

let doc
try {
  doc = yaml.load(fs.readFileSync(composePath, 'utf8'))
  console.log('YAML parses (js-yaml):                    OK  [lib v' + require('js-yaml/package.json').version + ']')
} catch (err) {
  console.error('YAML FAILED TO PARSE:', err.message)
  process.exit(1)
}

const services = doc.services || {}
const volumes = doc.volumes || {}
const networks = doc.networks || {}

console.log('top-level keys:                           ' + Object.keys(doc).sort().join(', '))
console.log('services:                                 ' + Object.keys(services).sort().join(', '))
console.log('volumes:                                  ' + Object.keys(volumes).join(', '))
console.log('networks:                                 ' + Object.keys(networks).join(', '))
console.log('')

for (const e of ['db', 'backend', 'frontend']) {
  if (!services[e]) errors.push(`expected service "${e}" is missing`)
}

for (const [name, svc] of Object.entries(services)) {
  if (svc.build) {
    const b = svc.build
    const ctx = typeof b === 'string' ? b : b.context
    const ctxAbs = path.resolve(root, ctx)
    if (!fs.existsSync(ctxAbs) || !fs.statSync(ctxAbs).isDirectory()) {
      errors.push(`${name}: build context does not exist: ${ctx}`)
      continue
    }
    const df = (typeof b === 'object' && b.dockerfile) ? b.dockerfile : 'Dockerfile'
    const dfAbs = path.resolve(ctxAbs, df)
    if (!fs.existsSync(dfAbs)) {
      errors.push(`${name}: Dockerfile not found: ${rel(dfAbs)}`)
    } else {
      console.log(`build OK        ${name.padEnd(9)} context=${ctx.padEnd(10)} dockerfile=${rel(dfAbs)}`)
      const dfText = fs.readFileSync(dfAbs, 'utf8').replace(/\\\r?\n/g, ' ')
      for (const m of dfText.matchAll(/^COPY\s+(?!--)(.+?)\s+\S+\s*$/gm)) {
        for (const tok of m[1].trim().split(/\s+/)) {
          if (tok.startsWith('--') || tok === '.') continue
          if (!fs.existsSync(path.resolve(ctxAbs, tok))) {
            errors.push(`${name}: Dockerfile COPY source missing from build context: ${tok}`)
          }
        }
      }
    }
  } else if (!svc.image) {
    errors.push(`${name}: has neither "image" nor "build"`)
  }

  if (!svc.healthcheck || !svc.healthcheck.test) {
    errors.push(`${name}: no healthcheck (required by this project)`)
  } else {
    console.log(`healthcheck OK  ${name.padEnd(9)} ${JSON.stringify(svc.healthcheck.test)}`)
  }

  const deps = svc.depends_on
  if (deps) {
    for (const d of Object.keys(deps)) {
      if (!services[d]) errors.push(`${name}: depends_on unknown service "${d}"`)
      else if (deps[d] && deps[d].condition !== 'service_healthy') {
        notes.push(`${name} -> ${d}: condition "${deps[d].condition}", not service_healthy`)
      }
    }
  }

  for (const v of svc.volumes || []) {
    const src = String(v).split(':')[0]
    if (!src.startsWith('.') && !src.startsWith('/') && !volumes[src]) {
      errors.push(`${name}: mounts undeclared named volume "${src}"`)
    }
  }
  for (const n of svc.networks || []) {
    if (!networks[n]) errors.push(`${name}: joins undeclared network "${n}"`)
  }
}

const backendEnv = (services.backend && services.backend.environment) || {}
const dbUrl = String(backendEnv.DATABASE_URL || '').trim()
if (!dbUrl) {
  errors.push('backend: DATABASE_URL is not set')
} else if (/localhost|127\.0\.0\.1/.test(dbUrl)) {
  errors.push('backend: DATABASE_URL points at localhost; inside Compose use the service name "db"')
} else if (!/@db:\d+\//.test(dbUrl)) {
  errors.push(`backend: DATABASE_URL does not address the "db" service: ${dbUrl}`)
} else {
  console.log('DATABASE_URL host:                        OK (addresses the "db" service)')
}

const feArgs = (((services.frontend || {}).build || {}).args) || {}
console.log('VITE_API_BASE_URL build arg:              ' + (feArgs.VITE_API_BASE_URL || '(uses Dockerfile default)'))

// Resolved values (interpolated manually, since Compose interpolation needs docker).
const resolved = {
  POSTGRES_USER: backendEnv.DATABASE_URL ? 'ok' : 'missing',
}
if (typeof backendEnv.DATABASE_URL === 'string' && backendEnv.DATABASE_URL.includes('${')) {
  notes.push('DATABASE_URL contains ${...} placeholders; values resolve at `docker compose up` time')
}

const secretPatterns = [
  [/AKIA[0-9A-Z]{16}/, 'AWS access key id'],
  [/\bsk-[A-Za-z0-9]{20,}/, 'OpenAI-style key'],
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, 'private key'],
  [/\bghp_[A-Za-z0-9]{36}/, 'GitHub token'],
  [/\bxox[baprs]-[A-Za-z0-9-]{10,}/, 'Slack token'],
]
const text = fs.readFileSync(composePath, 'utf8')
let secretFound = false
for (const [re, label] of secretPatterns) {
  if (re.test(text)) { errors.push(`compose file contains what looks like a real ${label}`); secretFound = true }
}
console.log('secret scan:                              ' + (secretFound ? 'FAIL' : 'OK (no credential patterns found)'))

console.log('')
if (notes.length) {
  console.log('Notes:')
  for (const n of notes) console.log('  - ' + n)
  console.log('')
}

if (errors.length) {
  console.log('STATIC COMPOSE VALIDATION: FAIL')
  for (const e of errors) console.log('  * ' + e)
  process.exit(1)
}
console.log('STATIC COMPOSE VALIDATION: PASS')
console.log('NOTE: structural + syntax check only. `docker compose config`,')
console.log('      `build` and `up` have NOT been run: Docker is not installed here.')
