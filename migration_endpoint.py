@app.route('/admin/migrate/hidden_columns', methods=['POST'])
def migrate_hidden_columns():
    """
    Admin endpoint to add is_hidden and hidden_at columns to deals table
    This can be called on Render to update the database schema

    Usage:
    curl -X POST https://scanner.teckstart.com/admin/migrate/hidden_columns \\
      -H "X-Migration-Key: teckstart_migrate_2025"
    """

    # Simple security check - require a secret key
    expected_key = os.getenv('MIGRATION_SECRET_KEY', 'teckstart_migrate_2025')
    provided_key = request.headers.get('X-Migration-Key')

    if provided_key != expected_key:
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401

    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        return jsonify({
            'success': False,
            'error': 'DATABASE_URL not configured'
        }), 500

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(database_url)

        results = []

        with engine.connect() as conn:
            # Check and add is_hidden column
            check_sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'deals'
            AND column_name = 'is_hidden';
            """

            result = conn.execute(text(check_sql))
            existing = result.fetchone()

            if not existing:
                logger.info("Adding is_hidden column to deals table...")

                alter_sql = """
                ALTER TABLE deals
                ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE;
                """

                conn.execute(text(alter_sql))
                conn.commit()

                results.append('is_hidden column added')
            else:
                logger.info("is_hidden column already exists - skipping")
                results.append('is_hidden column already exists')

            # Check and add hidden_at column
            check_sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'deals'
            AND column_name = 'hidden_at';
            """

            result = conn.execute(text(check_sql))
            existing = result.fetchone()

            if not existing:
                logger.info("Adding hidden_at column to deals table...")

                alter_sql = """
                ALTER TABLE deals
                ADD COLUMN hidden_at TIMESTAMP;
                """

                conn.execute(text(alter_sql))
                conn.commit()

                results.append('hidden_at column added')
            else:
                logger.info("hidden_at column already exists - skipping")
                results.append('hidden_at column already exists')

            engine.dispose()

            logger.info(f"Hidden columns migration completed: {results}")

            return jsonify({
                'success': True,
                'message': 'Successfully migrated hidden columns',
                'action': 'completed',
                'results': results
            })

    except Exception as e:
        logger.error(f"Hidden columns migration failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500