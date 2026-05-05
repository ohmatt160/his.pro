from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.resources.base_resource import BaseResource
from app.models.inventory import Inventory
from app.models.supplier import Supplier
from app.utils.decorators import role_required
from app.utils.validators import Validators
from app.extensions import db

inventory_ns = Namespace('inventory', description='Inventory management operations')

# Swagger models
inventory_model = inventory_ns.model('Inventory', {
    'facility_slug': fields.String(required=True),
    'name': fields.String(required=True),
    'sku': fields.String(required=True),
    'category': fields.String(required=True),
    'unit': fields.String(required=True),
    'reorder_level': fields.Integer(),
    'reorder_quantity': fields.Integer(),
    'current_stock': fields.Integer(),
    'expiry_date': fields.String(),
    'supplier_id': fields.String(),
    'unit_cost': fields.Float()
})

inventory_update_model = inventory_ns.model('InventoryUpdate', {
    'name': fields.String(),
    'sku': fields.String(),
    'category': fields.String(),
    'unit': fields.String(),
    'reorder_level': fields.Integer(),
    'reorder_quantity': fields.Integer(),
    'expiry_date': fields.String(),
    'supplier_id': fields.String(),
    'unit_cost': fields.Float()
})

stock_update_model = inventory_ns.model('StockUpdate', {
    'current_stock': fields.Integer(required=True),
    'adjustment_type': fields.String()  # addition/reduction/set
})


class InventoryListResource(BaseResource):
    """Resource for listing and creating inventory items"""
    
    @role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')
    def get(self):
        """Get paginated list of inventory items"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Filters
        facility_slug = request.args.get('facility_slug')
        category = request.args.get('category')
        search = request.args.get('search')
        
        if per_page > 100:
            per_page = 100
        
        # Get current user
        current_user = self.get_current_user()
        
        # Build query based on user role and facility
        query = Inventory.query.filter_by(is_active=True)
        
        # Filter by facility if not admin
        if current_user.role != 'ADMIN' and current_user.facility_slug:
            query = query.filter_by(facility_slug=current_user.facility_slug)
        elif facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        
        if category:
            query = query.filter_by(category=category)
        
        if search:
            query = query.filter(
                db.or_(
                    Inventory.name.ilike(f'%{search}%'),
                    Inventory.sku.ilike(f'%{search}%')
                )
            )
        
        # Order by name
        query = query.order_by(Inventory.name)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        items = pagination.items
        
        # Build response with supplier info
        result = []
        for item in items:
            item_data = item.to_dict()
            item_data['needs_reorder'] = item.needs_reorder
            if item.supplier:
                item_data['supplier_name'] = item.supplier.name
            result.append(item_data)
        
        return self.handle_response(data={
            'inventory_items': result,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    
    @role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')
    @inventory_ns.expect(inventory_model)
    def post(self):
        """Add a new inventory item"""
        data = request.get_json()
        
        # Validate required fields
        if not data.get('facility_slug'):
            return self.handle_error("Facility slug is required", 400)
        if not data.get('name'):
            return self.handle_error("Item name is required", 400)
        if not data.get('sku'):
            return self.handle_error("SKU is required", 400)
        if not data.get('category'):
            return self.handle_error("Category is required", 400)
        if not data.get('unit'):
            return self.handle_error("Unit is required", 400)
        
        # Validate category
        if data['category'] not in Inventory.CATEGORIES:
            return self.handle_error(f"Invalid category. Must be one of: {', '.join(Inventory.CATEGORIES)}", 400)
        
        # Check for duplicate SKU in same facility
        existing = Inventory.query.filter_by(
            facility_slug=data['facility_slug'],
            sku=data['sku'],
            is_active=True
        ).first()
        if existing:
            return self.handle_error("An item with this SKU already exists in this facility", 400)
        
        # Validate supplier if provided
        if data.get('supplier_id'):
            supplier = Supplier.query.get(data['supplier_id'])
            if not supplier:
                return self.handle_error("Supplier not found", 404)
        
        # Create inventory item
        from datetime import datetime
        from decimal import Decimal
        
        inventory = Inventory(
            facility_slug=data['facility_slug'],
            name=Validators.sanitize_string(data['name']),
            sku=Validators.sanitize_string(data['sku']),
            category=data['category'],
            unit=data['unit'],
            reorder_level=data.get('reorder_level', 0),
            reorder_quantity=data.get('reorder_quantity', 0),
            current_stock=data.get('current_stock', 0),
            supplier_id=data.get('supplier_id'),
            unit_cost=Decimal(str(data.get('unit_cost', 0)))
        )
        
        # Parse expiry date if provided
        if data.get('expiry_date'):
            try:
                inventory.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            except ValueError:
                return self.handle_error("Invalid expiry_date format. Use YYYY-MM-DD", 400)
        
        db.session.add(inventory)
        db.session.commit()
        
        return self.handle_response(
            data=inventory.to_dict(),
            message="Inventory item created successfully",
            status_code=201
        )


class InventoryResource(BaseResource):
    """Resource for individual inventory item operations"""
    
    @role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER', 'DOCTOR', 'NURSE')
    def get(self, item_id):
        """Get inventory item by ID"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        inventory = Inventory.query.filter_by(id=item_id, facility_slug=facility_slug).first()
        
        if not inventory:
            return self.handle_error("Inventory item not found", 404)
        
        item_data = inventory.to_dict()
        item_data['needs_reorder'] = inventory.needs_reorder
        if inventory.supplier:
            item_data['supplier_name'] = inventory.supplier.name
        
        return self.handle_response(data=item_data)
    
    @role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')
    @inventory_ns.expect(inventory_update_model)
    def put(self, item_id):
        """Update inventory item"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        inventory = Inventory.query.filter_by(id=item_id, facility_slug=facility_slug).first()
        
        if not inventory:
            return self.handle_error("Inventory item not found", 404)
        
        data = request.get_json()
        
        # Update fields
        if 'name' in data and data['name']:
            inventory.name = Validators.sanitize_string(data['name'])
        if 'sku' in data and data['sku']:
            # Check for duplicate SKU
            existing = Inventory.query.filter(
                Inventory.facility_slug == inventory.facility_slug,
                Inventory.sku == data['sku'],
                Inventory.id != item_id,
                Inventory.is_active == True
            ).first()
            if existing:
                return self.handle_error("An item with this SKU already exists", 400)
            inventory.sku = Validators.sanitize_string(data['sku'])
        if 'category' in data:
            if data['category'] not in Inventory.CATEGORIES:
                return self.handle_error(f"Invalid category. Must be one of: {', '.join(Inventory.CATEGORIES)}", 400)
            inventory.category = data['category']
        if 'unit' in data:
            inventory.unit = data['unit']
        if 'reorder_level' in data:
            inventory.reorder_level = data['reorder_level']
        if 'reorder_quantity' in data:
            inventory.reorder_quantity = data['reorder_quantity']
        if 'supplier_id' in data:
            if data['supplier_id']:
                supplier = Supplier.query.get(data['supplier_id'])
                if not supplier:
                    return self.handle_error("Supplier not found", 404)
            inventory.supplier_id = data['supplier_id']
        if 'unit_cost' in data:
            from decimal import Decimal
            inventory.unit_cost = Decimal(str(data['unit_cost']))
        
        # Update expiry date if provided
        if 'expiry_date' in data and data['expiry_date']:
            from datetime import datetime
            try:
                inventory.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            except ValueError:
                return self.handle_error("Invalid expiry_date format. Use YYYY-MM-DD", 400)
        
        db.session.commit()
        
        return self.handle_response(
            data=inventory.to_dict(),
            message="Inventory item updated successfully"
        )
    
    @role_required('ADMIN')
    def delete(self, item_id):
        """Deactivate inventory item (soft delete)"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        inventory = Inventory.query.filter_by(id=item_id, facility_slug=facility_slug).first()
        
        if not inventory:
            return self.handle_error("Inventory item not found", 404)
        
        if inventory.current_stock > 0:
            return self.handle_error("Cannot delete item with current stock", 400)
        
        inventory.is_active = False
        db.session.commit()
        
        return self.handle_response(message="Inventory item deactivated successfully")


class InventoryStockResource(BaseResource):
    """Resource for updating inventory stock levels"""
    
    @role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')
    @inventory_ns.expect(stock_update_model)
    def put(self, item_id):
        """Update stock level"""
        # Get current user's facility
        current_user = self.get_current_user()
        facility_slug = current_user.facility_slug if current_user else None
        
        if not facility_slug:
            return self.handle_error("User is not associated with a facility", 400)
        
        # Filter by facility
        inventory = Inventory.query.filter_by(id=item_id, facility_slug=facility_slug).first()
        
        if not inventory:
            return self.handle_error("Inventory item not found", 404)
        
        data = request.get_json()
        adjustment_type = data.get('adjustment_type', 'set')
        new_stock = data.get('current_stock', 0)
        
        if adjustment_type == 'set':
            inventory.current_stock = new_stock
        elif adjustment_type == 'addition':
            inventory.current_stock += new_stock
        elif adjustment_type == 'reduction':
            if inventory.current_stock < new_stock:
                return self.handle_error("Insufficient stock for reduction", 400)
            inventory.current_stock -= new_stock
        else:
            return self.handle_error("Invalid adjustment_type. Must be: addition, reduction, or set", 400)
        
        db.session.commit()
        
        return self.handle_response(
            data=inventory.to_dict(),
            message="Stock level updated successfully"
        )


class InventoryLowStockResource(BaseResource):
    """Resource for getting low stock items"""
    
    @role_required('ADMIN', 'PHARMACIST', 'STORE_KEEPER')
    def get(self):
        """Get items below reorder level"""
        # Filters
        facility_slug = request.args.get('facility_slug')
        
        # Get current user
        current_user = self.get_current_user()
        
        # Build query
        query = Inventory.query.filter_by(is_active=True)
        
        # Filter by facility if not admin
        if current_user.role != 'ADMIN' and current_user.facility_slug:
            query = query.filter_by(facility_slug=current_user.facility_slug)
        elif facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        
        # Filter items that need reorder
        query = query.filter(Inventory.current_stock <= Inventory.reorder_level)
        
        items = query.order_by(Inventory.current_stock).all()
        
        result = []
        for item in items:
            item_data = item.to_dict()
            item_data['needs_reorder'] = True
            item_data['shortage_amount'] = item.reorder_level - item.current_stock
            if item.supplier:
                item_data['supplier_name'] = item.supplier.name
            result.append(item_data)
        
        return self.handle_response(data={
            'low_stock_items': result,
            'total': len(result)
        })


# Register resources
inventory_ns.add_resource(InventoryListResource, '')
inventory_ns.add_resource(InventoryResource, '/<string:item_id>')
inventory_ns.add_resource(InventoryStockResource, '/<string:item_id>/stock')
inventory_ns.add_resource(InventoryLowStockResource, '/low-stock')