import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'GlassTrax Bridge',
  description: 'REST API for GlassTrax ERP',
  // Use /guide in production (single port), /docs in Docker (nginx handles routing)
  base: process.env.VITEPRESS_BASE || '/docs/',

  // Ignore localhost links in documentation (they're examples, not real links)
  ignoreDeadLinks: [
    /^https?:\/\/localhost/,
    /^https?:\/\/127\.0\.0\.1/,
    /^https?:\/\/192\.168\./,
  ],

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }]
  ],

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'API Reference', link: '/api/' },
      { text: 'Portal', link: '/portal/' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Introduction',
          items: [
            { text: 'Getting Started', link: '/guide/getting-started' },
            { text: 'Configuration', link: '/guide/configuration' },
            { text: 'Authentication', link: '/guide/authentication' }
          ]
        },
        {
          text: 'Concepts',
          items: [
            { text: 'Applications', link: '/guide/applications' },
            { text: 'API Keys', link: '/guide/api-keys' },
            { text: 'Permissions', link: '/guide/permissions' }
          ]
        },
        {
          text: 'Deployment',
          items: [
            { text: 'Docker & Windows', link: '/guide/deployment' },
            { text: 'Agent Installer', link: '/guide/agent-installation' },
            { text: 'Agent Manual Setup', link: '/guide/agent-setup' }
          ]
        }
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Overview', link: '/api/' },
            { text: 'Authentication', link: '/api/authentication' },
            { text: 'Customers', link: '/api/customers' },
            { text: 'Orders', link: '/api/orders' },
            { text: 'Admin Endpoints', link: '/api/admin' }
          ]
        }
      ],
      '/portal/': [
        {
          text: 'Admin Portal',
          items: [
            { text: 'Overview', link: '/portal/' },
            { text: 'Dashboard', link: '/portal/dashboard' },
            { text: 'Managing Keys', link: '/portal/api-keys' },
            { text: 'Diagnostics', link: '/portal/diagnostics' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Codename-11/GlassTrax-Bridge' }
    ],

    footer: {
      message: 'Internal Documentation',
      copyright: 'GlassTrax Bridge'
    },

    search: {
      provider: 'local'
    }
  }
})
