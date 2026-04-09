export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'subject-max-length': [2, 'always', 72],
    'subject-full-stop': [2, 'never', '.'],
  },
};
