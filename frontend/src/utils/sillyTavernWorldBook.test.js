import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildSillyTavernWorldBook,
  countWorldBookEntries,
  createWorldBookFileName,
} from './sillyTavernWorldBook.js'

const sampleWorld = {
  id: 'world_1',
  name: '测试世界',
  era: '星际时代',
  anchor_time: '公元3000年',
  description: '一个测试用世界观。',
  writing_style: '冷峻史诗',
  entities: [
    {
      id: 'ent_1',
      name: '艾拉',
      type: '人物',
      aliases: ['星火', 'Aira'],
      attributes: {
        简介: '反抗军领袖。',
        阵营: '红色联合',
      },
      stages: [
        { name: '觉醒', era: '2998年', description: '第一次接触核心遗迹。' },
      ],
      relationships: [
        { target: '红色联合', type: '领袖', description: '共同组织地下行动。' },
      ],
    },
  ],
  events: [
    {
      id: 'evt_1',
      name: '晨星战役',
      date: '3001年',
      description: '红色联合夺回轨道城。',
      entities: ['艾拉', '红色联合'],
    },
  ],
  settings: {
    items: [
      {
        id: 'setting_1',
        name: '红色联合',
        settingType: 'setting',
        category: 'organization',
        aliases: ['赤盟'],
        description: '地下抵抗组织。',
        detailContent: '以分布式据点维持行动。',
        structuredDetail: {
          facts: [{ label: '总部', value: '轨道城' }],
        },
      },
      {
        id: 'collection_1',
        name: '组织集合',
        settingType: 'collection',
      },
    ],
  },
}

test('buildSillyTavernWorldBook creates SillyTavern entries object', () => {
  const book = buildSillyTavernWorldBook(sampleWorld)

  assert.equal(book.name, '测试世界')
  assert.equal(typeof book.entries, 'object')
  assert.equal(countWorldBookEntries(book), 4)
  assert.equal(book.extensions.worldfish.world_id, 'world_1')
})

test('overview entry is constant and contains world metadata', () => {
  const book = buildSillyTavernWorldBook(sampleWorld)
  const overview = book.entries['0']

  assert.equal(overview.constant, true)
  assert.deepEqual(overview.key, ['测试世界', '星际时代'])
  assert.match(overview.content, /世界观: 测试世界/)
  assert.match(overview.content, /时代背景: 星际时代/)
})

test('entity entry includes aliases, stages and relationships', () => {
  const book = buildSillyTavernWorldBook(sampleWorld)
  const entityEntry = Object.values(book.entries).find(entry => entry.comment.includes('艾拉'))

  assert.ok(entityEntry)
  assert.deepEqual(entityEntry.key, ['艾拉', '星火', 'Aira'])
  assert.match(entityEntry.content, /反抗军领袖/)
  assert.match(entityEntry.content, /成长阶段/)
  assert.match(entityEntry.content, /红色联合/)
})

test('export options can disable events and settings', () => {
  const book = buildSillyTavernWorldBook(sampleWorld, {
    includeEvents: false,
    includeSettings: false,
  })

  assert.equal(countWorldBookEntries(book), 2)
  assert.equal(Object.values(book.entries).some(entry => entry.comment.includes('晨星战役')), false)
  assert.equal(Object.values(book.entries).some(entry => entry.comment.includes('红色联合 · 设定')), false)
})

test('createWorldBookFileName sanitizes invalid file characters', () => {
  assert.equal(createWorldBookFileName({ name: 'A/B:C*D?' }), 'A_B_C_D_-worldbook.json')
})
