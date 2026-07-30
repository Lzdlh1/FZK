import { describe, it, expect } from 'vitest'
import { evaluate, extractVarRefs } from './engine'

describe('formula engine', () => {
  it('基础四则运算与变量替换', () => {
    const r = evaluate('{总长} - {吃线} * {端子数}', {
      总长: 1000,
      吃线: 12,
      端子数: 2,
    })
    expect(r.value).toBe(976)
    expect(r.substitutedExpression).toBe('1000 - 12 * 2')
    expect(r.dbRefs).toEqual([])
  })

  it('ROUND 函数', () => {
    const r = evaluate('ROUND({总长} - {吃线}*2, 1)', {
      总长: 1000,
      吃线: 12,
      端子数: 2,
    })
    expect(r.value).toBe(976)
  })

  it('IF 函数:条件分支', () => {
    const expr = 'IF({端子数}>2, {总长}-{吃线}*{端子数}, {总长})'
    expect(
      evaluate(expr, { 总长: 1000, 吃线: 12, 端子数: 2 }).value
    ).toBe(1000)
    expect(
      evaluate(expr, { 总长: 1000, 吃线: 12, 端子数: 3 }).value
    ).toBe(964)
  })

  it('幂运算右结合: 2^3^2 = 512', () => {
    const r = evaluate('2^3^2', {})
    expect(r.value).toBe(512)
  })

  it('extractVarRefs 去重保序', () => {
    expect(extractVarRefs('{a}+{b}*{c}')).toEqual(['a', 'b', 'c'])
  })

  it('extractVarRefs 去重', () => {
    expect(extractVarRefs('{a}+{a}+{b}')).toEqual(['a', 'b'])
  })

  it('除零抛错', () => {
    expect(() => evaluate('1/0', {})).toThrow()
  })

  it('未绑定变量抛错', () => {
    expect(() => evaluate('{x}+1', {})).toThrow('未绑定变量: x')
  })

  it('未知函数抛错', () => {
    expect(() => evaluate('FOO(1)', {})).toThrow('未知函数: FOO')
  })

  it('MAX 函数', () => {
    expect(evaluate('MAX(1, 5, 3)', {}).value).toBe(5)
  })

  it('MIN 函数', () => {
    expect(evaluate('MIN(1, 5, 3)', {}).value).toBe(1)
  })

  it('ABS 函数', () => {
    expect(evaluate('ABS(-5)', {}).value).toBe(5)
  })

  it('LEN 函数(字符串)', () => {
    expect(evaluate('LEN("hello")', {}).value).toBe(5)
  })

  it('比较运算符产生 1/0', () => {
    expect(evaluate('3 > 2', {}).value).toBe(1)
    expect(evaluate('2 > 3', {}).value).toBe(0)
    expect(evaluate('2 = 2', {}).value).toBe(1)
    expect(evaluate('2 <> 2', {}).value).toBe(0)
  })
})
