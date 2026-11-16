import fs from 'node:fs/promises';
import path from 'node:path';
import * as seed from '../src/shared/api/mocks/seed.ts';
const destination = process.argv[2];
if (!destination)
  throw new Error(
    'Usage: node --experimental-strip-types tests/export-real-fixture.mjs <new-directory>',
  );
// Refuse existing directories so this helper cannot overwrite production seed data.
await fs.mkdir(destination);
for (const [file, key] of Object.entries({
  persons: 'persons',
  organs: 'organs',
  positions: 'positions',
  authorities: 'authorities',
  appointments: 'appointments',
  kinships: 'kinships',
  companies: 'companies',
  company_roles: 'companyRoles',
  employments: 'employments',
  contracts: 'contracts',
  appeals: 'appeals',
})) {
  await fs.writeFile(path.join(destination, `${file}.json`), JSON.stringify(seed[key], null, 2));
}
console.log('Exported existing synthetic frontend fixtures for isolated API tests:', destination);
