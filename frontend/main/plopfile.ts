import type { NodePlopAPI } from 'plop';

export default function (plop: NodePlopAPI) {
  // ─── Component Generator ───────────────────────────────────────
  plop.setGenerator('component', {
    description: 'Create a React component',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Component name (PascalCase):',
      },
      {
        type: 'list',
        name: 'directory',
        message: 'Where to place the component:',
        choices: [
          { name: 'src/components/shared/', value: 'src/components/shared' },
          { name: 'src/components/layout/', value: 'src/components/layout' },
          { name: 'Feature module (specify)', value: 'feature' },
        ],
      },
      {
        type: 'input',
        name: 'featureName',
        message: 'Feature name:',
        when: (answers) => answers['directory'] === 'feature',
      },
      {
        type: 'confirm',
        name: 'isClient',
        message: 'Is this a client component?',
        default: false,
      },
    ],
    actions: (data) => {
      const dir =
        data?.directory === 'feature'
          ? `src/features/{{kebabCase featureName}}/components`
          : data?.directory;

      return [
        {
          type: 'add',
          path: `${dir}/{{kebabCase name}}.tsx`,
          templateFile: 'templates/component.tsx.hbs',
        },
        {
          type: 'add',
          path: `${dir}/{{kebabCase name}}.test.tsx`,
          templateFile: 'templates/component.test.tsx.hbs',
        },
      ];
    },
  });

  // ─── Hook Generator ──────────────��─────────────────────────────
  plop.setGenerator('hook', {
    description: 'Create a custom React hook',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Hook name (e.g., useMediaQuery):',
      },
      {
        type: 'list',
        name: 'directory',
        message: 'Where to place the hook:',
        choices: [
          { name: 'src/hooks/ (global)', value: 'src/hooks' },
          { name: 'Feature module (specify)', value: 'feature' },
        ],
      },
      {
        type: 'input',
        name: 'featureName',
        message: 'Feature name:',
        when: (answers) => answers['directory'] === 'feature',
      },
    ],
    actions: (data) => {
      const dir =
        data?.directory === 'feature'
          ? `src/features/{{kebabCase featureName}}/hooks`
          : data?.directory;

      return [
        {
          type: 'add',
          path: `${dir}/{{kebabCase name}}.ts`,
          templateFile: 'templates/hook.ts.hbs',
        },
        {
          type: 'add',
          path: `${dir}/{{kebabCase name}}.test.ts`,
          templateFile: 'templates/hook.test.ts.hbs',
        },
      ];
    },
  });

  // ─── Server Action Generator ─────────────��─────────────────────
  plop.setGenerator('action', {
    description: 'Create a Server Action with Zod schema',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Action name (e.g., createCheckout):',
      },
      {
        type: 'input',
        name: 'featureName',
        message: 'Feature name:',
      },
    ],
    actions: [
      {
        type: 'add',
        path: 'src/features/{{kebabCase featureName}}/actions/{{kebabCase name}}.ts',
        templateFile: 'templates/server-action.ts.hbs',
      },
    ],
  });

  // ─── Feature Module Generator ─────────��────────────────────────
  plop.setGenerator('feature', {
    description: 'Scaffold a full feature module',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Feature name:',
      },
    ],
    actions: [
      {
        type: 'add',
        path: 'src/features/{{kebabCase name}}/components/.gitkeep',
      },
      {
        type: 'add',
        path: 'src/features/{{kebabCase name}}/hooks/.gitkeep',
      },
      {
        type: 'add',
        path: 'src/features/{{kebabCase name}}/actions/.gitkeep',
      },
      {
        type: 'add',
        path: 'src/features/{{kebabCase name}}/schemas/.gitkeep',
      },
      {
        type: 'add',
        path: 'src/features/{{kebabCase name}}/types/.gitkeep',
      },
      {
        type: 'add',
        path: 'src/features/{{kebabCase name}}/api/.gitkeep',
      },
    ],
  });
}
