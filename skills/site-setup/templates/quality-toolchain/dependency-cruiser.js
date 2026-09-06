/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular dependencies lead to unpredictable runtime crashes and tight coupling.',
      from: {},
      to: {
        circular: true
      }
    },
    {
      name: 'no-orphans',
      comment: 'Modules that have no incoming or outgoing dependencies.',
      severity: 'warn',
      from: {
        orphan: true,
        pathNot: [
          '(^|/)\\.[^/]+', // dotfiles
          '\\.d\\.ts$',     // typescript definitions
          '(^|/)tsconfig\\.json$',
          '(^|/)package\\.json$'
        ]
      },
      to: {}
    },
    {
      name: 'ui-cannot-import-db-directly',
      comment: 'UI and Presentation layers must go through services/APIs and never access DB directly.',
      severity: 'error',
      from: {
        path: '^(src/components|src/app|src/pages)'
      },
      to: {
        path: '^(src/db|src/server/db|src/infrastructure/database)'
      }
    }
  ],
  options: {
    doNotFollow: {
      path: 'node_modules'
    },
    tsPreCompilationDeps: true,
    tsConfig: {
      fileName: 'tsconfig.json'
    },
    reporterOptions: {
      dot: {
        collapsePattern: 'node_modules/[^/]+'
      }
    }
  }
};
