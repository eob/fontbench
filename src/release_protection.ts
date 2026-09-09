import fs from 'node:fs';
import path from 'node:path';

function physicalPath(filename: string): string {
  let existing = path.resolve(filename);
  const suffix: string[] = [];
  while (!fs.existsSync(existing)) {
    if (fs.lstatSync(existing, { throwIfNoEntry: false })?.isSymbolicLink()) {
      throw new Error(`Cannot resolve output symlink: ${existing}`);
    }
    suffix.unshift(path.basename(existing));
    existing = path.dirname(existing);
  }
  return path.join(fs.realpathSync(existing), ...suffix);
}

export function assertMutableOutput(outputDir: string, repository = path.resolve(import.meta.dir, '..')): void {
  const destination = physicalPath(outputDir);
  const registry = path.join(repository, 'releases');
  for (const filename of fs.readdirSync(registry).filter(name => name.endsWith('.json'))) {
    const release = JSON.parse(fs.readFileSync(path.join(registry, filename), 'utf8'));
    for (const field of ['dataset_manifest', 'harbor_dataset']) {
      const value: unknown = release?.[field];
      if (typeof value !== 'string' || !value || path.isAbsolute(value) || value.includes('\\')
        || value.split('/').some(part => !part || part === '.' || part === '..')) {
        throw new Error(`Invalid ${field} in release registry ${filename}`);
      }
      const protectedDir = physicalPath(path.join(repository, field === 'dataset_manifest' ? path.dirname(value) : value));
      const relative = path.relative(destination, protectedDir);
      if (destination === protectedDir || destination.startsWith(protectedDir + path.sep)
        || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith('..' + path.sep))) {
        throw new Error(`Frozen release output: ${outputDir} overlaps ${filename} ${field}; use a separate candidate directory`);
      }
    }
  }
}
