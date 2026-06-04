/** @type {import('jest').Config} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: ['**/*.test.ts'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  collectCoverageFrom: [
    'implementation/**/*.ts',
    '!implementation/**/*.d.ts',
  ],
  transform: {
    '^.+\\.tsx?$': ['ts-jest', {
      tsconfig: 'tsconfig.test.json',
      diagnostics: false
    }]
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/implementation/$1'
  },
  transformIgnorePatterns: [
    'node_modules/(?!(uuid)/)'
  ],

};
