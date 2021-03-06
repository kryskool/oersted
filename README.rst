Œrsted
======

Installation
------------

Use pip to install this version of Oersted::

    pip install git+https://github.com/kryskool/oersted.git

If you have already install and compile lxml, add arguments --no-deps::

    pip install --no-deps git+https://github.com/kryskool/oersted.git

or download a zip and use::

    python setup.py install

Examples
--------

Œrsted is a library to access OpenERP objects pythonicaly. It allows you to do
stuff like ::

    >>> from oersted import OEClient
    >>> oeclient = OEClient('localhost')
    >>> oeclient.login('database', 'admin', 'password')
    >>> Product = oeclient.create_browse('database', 'product.product')
    >>> product = Product(1)  # Fetch product with id == 1
    >>> product.name
    u'Flan au Chocolat'
    >>> product.categ_id
    <oersted.browse.product.category object at 0xb74abf6c>
    >>> print product.categ_id
    <product.category 4@database>
    >>> product.categ_id.name
    u'Gourmandises'
    >>> for seller_info in product.seller_ids:
    ...     print seller_info, seller_info.name.name
    ...
    <product.supplierinfo 3@database> Chocolate Ltd
    >>>

Œrsted also provide a way to use defaults/onchange's and view specific stuffs::

    >>> View = oeclient.create_view('database', 'sale.view_order_form')
    >>> n_view = View()
    >>> n_view.partner_id = Partner(4)
    >>> n_view.pricelist_id
    <oersted.browse.product.pricelist object at 0xb56ghc3>

That some might find usefull

Developer
---------

To install as developer::

    python setup.py develop

Since Python 2.6 install the library in your home::

    python setup.py develop --user

