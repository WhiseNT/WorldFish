export const builtinFrontendModules = {
  'world-builder': {
    routes: ['/world-builder'],
    entryLabel: '构建世界观',
  },
  rag: {
    routes: ['/rag'],
    entryLabel: '知识库',
  },
  simulation: {
    routes: ['/simulation/new', '/simulation/:id'],
    entryLabel: '开始推演',
  },
  collaboration: {
    routes: ['/collab'],
    entryLabel: '联机房间',
  },
  settings: {
    routes: ['/settings/llm', '/settings/modules'],
    entryLabel: '设置',
  },
}

export function frontendModuleOfRoute(path) {
  return Object.entries(builtinFrontendModules).find(([, module]) => {
    return module.routes.some(route => route === path)
  })?.[0]
}
