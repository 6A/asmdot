import typeinfo, private/helpers

template `shl`(a: bool, b: untyped): untyped =
  cast[type b](a) shl b

include private/arm
