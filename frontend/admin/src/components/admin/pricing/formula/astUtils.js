export function expressionToText(expr) {
  if (!expr || typeof expr !== 'object') return '';
  if ('const' in expr) return expr.const;
  if ('var' in expr) return expr.var;
  if ('ref' in expr) return expr.ref;
  if ('op' in expr && Array.isArray(expr.args)) {
    return expr.args.map(expressionToText).join(` ${expr.op} `);
  }
  if ('fn' in expr && Array.isArray(expr.args)) {
    return `${expr.fn}(${expr.args.map(expressionToText).join(', ')})`;
  }
  return JSON.stringify(expr);
}

export function astToBindings(ast) {
  if (!ast?.bindings) return [];
  return ast.bindings.map((b) => ({
    ...b,
    _exprText: expressionToText(b.expr),
  }));
}

export function bindingsToAst(bindings) {
  return {
    version: 1,
    bindings: bindings.map(({ _exprText, ...rest }) => rest),
  };
}
