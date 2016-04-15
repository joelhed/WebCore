# encoding: utf-8

from __future__ import unicode_literals

from marrow.package.host import ExtensionManager

from .context import Context


log = __import__('logging').getLogger(__name__)


class WebExtensions(ExtensionManager):
	"""Principal WebCore extension manager.
	
	This extension registry handles loading and access to extensions as well as the collection of standard WebCore
	Extension API callbacks. Reference the `SIGNALS` constant for a list of the individual callbacks that can be
	utilized and their meanings, and the `extension.py` example for more detailed descriptions.
	
	At a basic level an extension is a class. That's it; attributes and methods are used to inform the manager
	of extension metadata and register callbacks for certain events. The most basic extension is one that does
	nothing:
	
		class Extension:
			pass
	
	To register your extension, add a reference to it to your project's `entry_points` in your project's `setup.py`
	under the `web.extension` namespace:
	
		...
		
		setup(
			...,
			entry_points = {'web.extension': [
					'example = myapp:Extension',
				]},
		)
	
	Your extension may define several additional properties:
	
		* `provides` -- declare tags describing the features offered by the plugin
		* `needs` -- delcare the tags that must be present for this extension to function
		* `uses` -- declare the tags that must be evaluated prior to this extension, but aren't hard requirements
		* `first` -- declare that this extension is a dependency of all other non-first extensions
		* `last` -- declare that this extension depends on all other non-last extensions
	
	Tags used as `provides` values should also be registered as `web.extension` entry points.
	"""
	
	SIGNALS = (  # Extension hooks.
			'start',  # Executed during Application construction.
			'stop',  # Executed when (and if) the serve() server returns.
			'graceful',  # Executed when (and if) the process is instructed to reload configuration.
			'prepare',  # Executed during initial request processing.
			'dispatch',  # Executed once for each dispatch event.
			'before',  # Executed after all extension `prepare` methods have been called, prior to dispatch.
			'after',  # Executed after dispatch has returned and the response populated.
			'mutate',  # Inspect and potentially mutate arguments to the handler prior to execution.
			'transform',  # Transform the result returned by the handler and apply it to the response.
			'middleware',  # Executed to allow WSGI middleware wrapping.
		)
	
	__isabstractmethod__ = False  # Work around a Python 3.4+ issue when attaching to the context.
	
	def __init__(self, ctx):
		"""Extension registry constructor.
		
		The extension registry is not meant to be instantiated by third-party software. Instead, access the registry
		as an attribute of the current Application or Request context: `context.extension`
		"""
		
		# Currently, this uses some application-internal shenanigans to construct the initial extension set.
		
		# TODO: Do a touch more than this, such as named plugin loading / configuration unpacking for dict/yaml-
		# based loading.
		
		self.feature = set()  # Track the active `provides` tags.
		self.all = self.order(ctx.app.config['extensions'])  # Needs/uses/provides-dependency ordered active extensions.
		signals = {signal: [] for signal in self.SIGNALS}  # Prepare the known callback sets.
		
		for ext in self.all:
			self.feature.update(getattr(ext, 'provides', []))  # Enable those flags.
			
			for mn in self.SIGNALS:  # Attach any callbacks that might exist.
				m = getattr(ext, mn, None)
				if m: signals[mn].append(m)
			
			if hasattr(ext, '__call__'):  # This one is aliased; the extension itself is treated as WSGI middleware.
				signals['middleware'].append(ext)
		
		# Certain operations act as a stack, i.e. "before" are executed in dependency order, but "after" are executed
		# in reverse dependency order.  This is also the case with "mutate" (incoming) and "transform" (outgoing).
		signals['after'].reverse()
		signals['transform'].reverse()
		signals['middleware'].reverse()
		
		self.signal = Context(**{k: tuple(v) for k, v in signals.items()})  # Packaged up, ready to go.
		self.signal['pre'] = tuple(signals['prepare'] + signals['before'])  # Save a chain() on each request.
		
		super(WebExtensions, self).__init__('web.extension')
