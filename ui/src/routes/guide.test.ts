import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const uiRoot = process.cwd();
const repoRoot = join(uiRoot, '..');
const guide = readFileSync(join(repoRoot, 'docs', 'ui-guide.html'), 'utf8');
const named = [...new Set([...guide.matchAll(/<code>(ui\/src\/[^<\s]+\.\w+)<\/code>/g)].map((match) => match[1]!))];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    return entry.isDirectory() ? sourceFiles(path) : [relative(repoRoot, path).replaceAll('\\', '/')];
  });
}

describe('docs/ui-guide.html', () => {
  it('names only files that exist', () => {
    expect(named.filter((path) => !existsSync(join(repoRoot, path)))).toEqual([]);
  });

  it('covers every source file', () => {
    const sources = sourceFiles(join(uiRoot, 'src')).filter((path) => !/\.test\.tsx?$/.test(path));
    expect(sources.filter((path) => !named.includes(path))).toEqual([]);
  });
});
