/**
 * 公式引擎(前端 TS 镜像,与后端 Python 严格一致)。
 *
 * 文法:
 *   expr        -> comparison
 *   comparison  -> additive ( (> | < | >= | <= | = | <>) additive )*
 *   additive    -> multiplicative ( (+ | -) multiplicative )*
 *   multiplicative -> power ( (* | /) power )*
 *   power       -> unary ( ^ power )?     // 右结合
 *   unary       -> (- | +)? primary
 *   primary     -> number | {var} | string | func(args) | ( expr )
 *
 * 变量引用 {name} 替换为 values[name];缺失抛 Error("未绑定变量: name")。
 * 比较运算符产生 1/0。^ 右结合。
 * 函数白名单(大小写不敏感):ROUND MAX MIN IF ABS LEN
 */

export interface EvaluateResult {
  value: number
  substitutedExpression: string
  dbRefs: unknown[]
}

type Value = number | string

type TokenType =
  | 'NUMBER'
  | 'VAR'
  | 'STRING'
  | 'IDENT'
  | 'PLUS'
  | 'MINUS'
  | 'STAR'
  | 'SLASH'
  | 'CARET'
  | 'LPAREN'
  | 'RPAREN'
  | 'COMMA'
  | 'GT'
  | 'LT'
  | 'GE'
  | 'LE'
  | 'EQ'
  | 'NE'
  | 'EOF'

interface Token {
  type: TokenType
  /** 原始文本(变量名/标识符/字符串内容) */
  value: string
  num?: number
  pos: number
}

function isDigit(c: string): boolean {
  return c >= '0' && c <= '9'
}

function isIdentStart(c: string): boolean {
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || c === '_'
}

function isIdentPart(c: string): boolean {
  return isIdentStart(c) || isDigit(c)
}

/** 格式化数值:整数去 .0 */
function formatNum(v: number): string {
  if (Number.isInteger(v)) return String(v)
  return String(v)
}

function tokenize(expr: string): Token[] {
  const tokens: Token[] = []
  let i = 0
  const n = expr.length
  while (i < n) {
    const c = expr[i]
    // 空白
    if (c === ' ' || c === '\t' || c === '\n' || c === '\r') {
      i++
      continue
    }
    const pos = i
    // 数字
    if (isDigit(c) || (c === '.' && isDigit(expr[i + 1] ?? ''))) {
      let j = i
      let dotSeen = false
      while (j < n && (isDigit(expr[j]) || (expr[j] === '.' && !dotSeen))) {
        if (expr[j] === '.') dotSeen = true
        j++
      }
      const text = expr.slice(i, j)
      tokens.push({ type: 'NUMBER', value: text, num: parseFloat(text), pos })
      i = j
      continue
    }
    // 变量引用 {name}(支持中文)
    if (c === '{') {
      let j = i + 1
      while (j < n && expr[j] !== '}') j++
      if (j >= n) throw new Error('词法错误: 未闭合的变量引用 {')
      const name = expr.slice(i + 1, j).trim()
      tokens.push({ type: 'VAR', value: name, pos })
      i = j + 1
      continue
    }
    // 字符串字面量
    if (c === '"') {
      let j = i + 1
      let s = ''
      while (j < n && expr[j] !== '"') {
        s += expr[j]
        j++
      }
      if (j >= n) throw new Error('词法错误: 未闭合的字符串 "')
      tokens.push({ type: 'STRING', value: s, pos })
      i = j + 1
      continue
    }
    // 标识符(函数名)
    if (isIdentStart(c)) {
      let j = i
      while (j < n && isIdentPart(expr[j])) j++
      tokens.push({ type: 'IDENT', value: expr.slice(i, j), pos })
      i = j
      continue
    }
    // 双字符运算符
    const two = expr.slice(i, i + 2)
    if (two === '>=') {
      tokens.push({ type: 'GE', value: '>=', pos })
      i += 2
      continue
    }
    if (two === '<=') {
      tokens.push({ type: 'LE', value: '<=', pos })
      i += 2
      continue
    }
    if (two === '<>') {
      tokens.push({ type: 'NE', value: '<>', pos })
      i += 2
      continue
    }
    // 单字符运算符
    switch (c) {
      case '+':
        tokens.push({ type: 'PLUS', value: '+', pos })
        break
      case '-':
        tokens.push({ type: 'MINUS', value: '-', pos })
        break
      case '*':
        tokens.push({ type: 'STAR', value: '*', pos })
        break
      case '/':
        tokens.push({ type: 'SLASH', value: '/', pos })
        break
      case '^':
        tokens.push({ type: 'CARET', value: '^', pos })
        break
      case '(':
        tokens.push({ type: 'LPAREN', value: '(', pos })
        break
      case ')':
        tokens.push({ type: 'RPAREN', value: ')', pos })
        break
      case ',':
        tokens.push({ type: 'COMMA', value: ',', pos })
        break
      case '>':
        tokens.push({ type: 'GT', value: '>', pos })
        break
      case '<':
        tokens.push({ type: 'LT', value: '<', pos })
        break
      case '=':
        tokens.push({ type: 'EQ', value: '=', pos })
        break
      default:
        throw new Error(`词法错误: 无法识别的字符 "${c}"`)
    }
    i++
  }
  tokens.push({ type: 'EOF', value: '', pos: n })
  return tokens
}

class Parser {
  private tokens: Token[]
  private pos = 0
  private values: Record<string, number>

  constructor(tokens: Token[], values: Record<string, number>) {
    this.tokens = tokens
    this.values = values
  }

  private peek(): Token {
    return this.tokens[this.pos]
  }

  private next(): Token {
    return this.tokens[this.pos++]
  }

  private expect(type: TokenType): Token {
    const t = this.tokens[this.pos]
    if (t.type !== type) {
      throw new Error(`语法错误: 期望 ${type} 但得到 ${t.type}`)
    }
    return this.tokens[this.pos++]
  }

  parse(): Value {
    const v = this.parseExpr()
    if (this.peek().type !== 'EOF') {
      throw new Error('语法错误: 表达式后存在多余内容')
    }
    return v
  }

  private parseExpr(): Value {
    return this.parseComparison()
  }

  private parseComparison(): Value {
    let left = this.parseAdditive()
    for (;;) {
      const t = this.peek().type
      if (
        t !== 'GT' &&
        t !== 'LT' &&
        t !== 'GE' &&
        t !== 'LE' &&
        t !== 'EQ' &&
        t !== 'NE'
      ) {
        break
      }
      this.next()
      const right = this.parseAdditive()
      const l = this.toNum(left)
      const r = this.toNum(right)
      let res: number
      switch (t) {
        case 'GT':
          res = l > r ? 1 : 0
          break
        case 'LT':
          res = l < r ? 1 : 0
          break
        case 'GE':
          res = l >= r ? 1 : 0
          break
        case 'LE':
          res = l <= r ? 1 : 0
          break
        case 'EQ':
          res = l === r ? 1 : 0
          break
        case 'NE':
          res = l !== r ? 1 : 0
          break
        default:
          res = 0
      }
      left = res
    }
    return left
  }

  private parseAdditive(): Value {
    let left = this.parseMultiplicative()
    for (;;) {
      const t = this.peek().type
      if (t !== 'PLUS' && t !== 'MINUS') break
      this.next()
      const right = this.parseMultiplicative()
      const l = this.toNum(left)
      const r = this.toNum(right)
      left = t === 'PLUS' ? l + r : l - r
    }
    return left
  }

  private parseMultiplicative(): Value {
    let left = this.parsePower()
    for (;;) {
      const t = this.peek().type
      if (t !== 'STAR' && t !== 'SLASH') break
      this.next()
      const right = this.parsePower()
      const l = this.toNum(left)
      const r = this.toNum(right)
      if (t === 'STAR') {
        left = l * r
      } else {
        if (r === 0) throw new Error('除零错误')
        left = l / r
      }
    }
    return left
  }

  private parsePower(): Value {
    const base = this.parseUnary()
    if (this.peek().type === 'CARET') {
      this.next()
      // 右结合:递归调用 parsePower
      const exp = this.parsePower()
      const b = this.toNum(base)
      const e = this.toNum(exp)
      return Math.pow(b, e)
    }
    return base
  }

  private parseUnary(): Value {
    const t = this.peek().type
    if (t === 'MINUS') {
      this.next()
      return -this.toNum(this.parseUnary())
    }
    if (t === 'PLUS') {
      this.next()
      return this.parseUnary()
    }
    return this.parsePrimary()
  }

  private parsePrimary(): Value {
    const t = this.peek()
    switch (t.type) {
      case 'NUMBER':
        this.next()
        return t.num!
      case 'VAR': {
        this.next()
        const name = t.value
        if (!(name in this.values)) {
          throw new Error(`未绑定变量: ${name}`)
        }
        return this.values[name]
      }
      case 'STRING':
        this.next()
        return t.value
      case 'LPAREN': {
        this.next()
        const v = this.parseExpr()
        this.expect('RPAREN')
        return v
      }
      case 'IDENT':
        return this.parseFunction()
      default:
        throw new Error(`语法错误: 意外的 token ${t.type}`)
    }
  }

  private parseFunction(): Value {
    const nameTok = this.next()
    const origName = nameTok.value
    const name = origName.toUpperCase()
    this.expect('LPAREN')
    const args: Value[] = []
    if (this.peek().type !== 'RPAREN') {
      args.push(this.parseExpr())
      while (this.peek().type === 'COMMA') {
        this.next()
        args.push(this.parseExpr())
      }
    }
    this.expect('RPAREN')
    return this.callFunction(name, origName, args)
  }

  private callFunction(name: string, origName: string, args: Value[]): Value {
    switch (name) {
      case 'ROUND': {
        if (args.length !== 2) {
          throw new Error('参数数量错误: ROUND 需要 2 个参数')
        }
        const x = this.toNum(args[0])
        const n = this.toNum(args[1])
        const factor = Math.pow(10, n)
        return Math.round(x * factor) / factor
      }
      case 'MAX': {
        if (args.length < 1) {
          throw new Error('参数数量错误: MAX 至少需要 1 个参数')
        }
        return Math.max(...args.map((a) => this.toNum(a)))
      }
      case 'MIN': {
        if (args.length < 1) {
          throw new Error('参数数量错误: MIN 至少需要 1 个参数')
        }
        return Math.min(...args.map((a) => this.toNum(a)))
      }
      case 'IF': {
        if (args.length !== 3) {
          throw new Error('参数数量错误: IF 需要 3 个参数')
        }
        const c = this.toNum(args[0])
        return c !== 0 ? args[1] : args[2]
      }
      case 'ABS': {
        if (args.length !== 1) {
          throw new Error('参数数量错误: ABS 需要 1 个参数')
        }
        return Math.abs(this.toNum(args[0]))
      }
      case 'LEN': {
        if (args.length !== 1) {
          throw new Error('参数数量错误: LEN 需要 1 个参数')
        }
        const a = args[0]
        const s = typeof a === 'string' ? a : formatNum(this.toNum(a))
        return s.length
      }
      default:
        throw new Error(`未知函数: ${origName}`)
    }
  }

  private toNum(v: Value): number {
    if (typeof v === 'number') return v
    throw new Error('类型错误: 期望数值但得到字符串')
  }
}

/**
 * 求值公式表达式。
 * @param expression 公式文本,变量用 {name} 引用
 * @param values 变量名 -> 数值
 * @returns { value, substitutedExpression, dbRefs }
 */
export function evaluate(
  expression: string,
  values: Record<string, number>
): EvaluateResult {
  const tokens = tokenize(expression)
  const parser = new Parser(tokens, values)
  const result = parser.parse()
  if (typeof result !== 'number') {
    throw new Error('表达式结果不是数值')
  }
  // substitutedExpression: 把 {var} 替换成数值(整数去 .0)
  const substitutedExpression = expression.replace(
    /\{([^}]+)\}/g,
    (_m, name: string) => {
      const key = name.trim()
      if (!(key in values)) {
        throw new Error(`未绑定变量: ${key}`)
      }
      return formatNum(values[key])
    }
  )
  return { value: result, substitutedExpression, dbRefs: [] }
}

/**
 * 提取表达式中所有 {var} 引用名,去重保序。
 */
export function extractVarRefs(expression: string): string[] {
  const refs: string[] = []
  const seen = new Set<string>()
  const re = /\{([^}]+)\}/g
  let m: RegExpExecArray | null
  while ((m = re.exec(expression)) !== null) {
    const name = m[1].trim()
    if (!seen.has(name)) {
      seen.add(name)
      refs.push(name)
    }
  }
  return refs
}
