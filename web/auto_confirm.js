const postgres = require('postgres');

const sql = postgres('postgresql://postgres:cats-thesis-2026@db.wkezsyjvyjciwnnngngq.supabase.co:5432/postgres');

async function migrate() {
    try {
        console.log("Starting auto-confirm migration...");
        
        await sql.unsafe(`
            CREATE OR REPLACE FUNCTION public.auto_confirm_email()
            RETURNS TRIGGER AS $$
            BEGIN
              NEW.email_confirmed_at = now();
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        `);

        await sql.unsafe(`DROP TRIGGER IF EXISTS on_auth_user_created_auto_confirm ON auth.users;`);

        await sql.unsafe(`
            CREATE TRIGGER on_auth_user_created_auto_confirm
              BEFORE INSERT ON auth.users
              FOR EACH ROW EXECUTE FUNCTION public.auto_confirm_email();
        `);

        // Update existing unconfirmed users
        await sql.unsafe(`
            UPDATE auth.users 
            SET email_confirmed_at = now() 
            WHERE email_confirmed_at IS NULL;
        `);

        console.log("Migration successful");
    } catch (e) {
        console.error("Migration failed", e);
    } finally {
        await sql.end();
    }
}
migrate();
