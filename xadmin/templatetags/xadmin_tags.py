import re

from django import template
from django.template import Library
from django.utils.html import escape
from django.utils.safestring import mark_safe

from xadmin.util import static, vendor as util_vendor

register = Library()


@register.simple_tag(takes_context=True)
def username_field(context):
	"""Get the userame based on the variable [USERNAME_FIELD]"""
	return getattr(context['original'], context['original'].USERNAME_FIELD)


@register.simple_tag(takes_context=True)
def view_block(context, block_name, *args, **kwargs):
	if 'admin_view' not in context:
		return ""

	admin_view = context['admin_view']
	nodes = []
	method_name = 'block_%s' % block_name.replace('-', '_')

	# Cancel the execution of the block in the view.
	show_block_view = getattr(admin_view, "show_block_view", None)
	block_funcs = []
	for view in [admin_view] + admin_view.plugins:
		block_func = getattr(view, method_name, None)
		if block_func and callable(block_func):
			if callable(show_block_view) and not show_block_view(view, block_name):
				continue
			block_funcs.append((getattr(block_func, "priority", 10), block_func))
	for _, block_func in sorted(block_funcs, key=lambda x: x[0],
	                            reverse=True):
		result = block_func(context, nodes, *args, **kwargs)
		if result and isinstance(result, str):
			nodes.append(result)

	if nodes:
		return mark_safe(''.join(nodes))
	else:
		return ""


@register.filter
def admin_urlname(value, arg):
	return 'xadmin:%s_%s_%s' % (value.app_label, value.model_name, arg)


static = register.simple_tag(static)


@register.filter
def xslugify(value):
	return re.sub(r'\W+', "_", value, re.I)


@register.simple_tag(takes_context=True)
def vendor(context, *tags):
	return util_vendor(*tags).render()


class BlockcaptureNode(template.Node):
	"""https://chriskief.com/2013/11/06/conditional-output-of-a-django-block/"""

	def __init__(self, nodelist, varname, safe=False):
		self.nodelist = nodelist
		self.varname = varname
		self.safe = safe

	def render(self, context):
		output = self.nodelist.render(context)
		context[self.varname] = mark_safe(output) if self.safe else escape(output)
		return ''


@register.tag(name='blockcapture')
def do_blockcapture(parser, token):
	nodelist = parser.parse(('endblockcapture',))
	parser.delete_first_token()

	tokens = token.split_contents()

	if len(tokens) < 2:
		raise template.TemplateSyntaxError(f"'{tokens[0]}' node requires a variable name.")

	args, kwargs = [], {}
	for token in tokens[1:]:
		if token.find("=") != -1:
			name, value = token.split("=")
			kwargs[name] = parser.compile_filter(value)
		else:
			args.append(token)
	return BlockcaptureNode(nodelist, *args, **kwargs)
