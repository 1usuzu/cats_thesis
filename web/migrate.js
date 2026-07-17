const postgres = require('postgres');

const sql = postgres('postgresql://postgres:cats-thesis-2026@db.wkezsyjvyjciwnnngngq.supabase.co:5432/postgres');

async function migrate() {
    try {
        console.log("Starting migration...");
        
        await sql.unsafe(`
            CREATE TABLE IF NOT EXISTS public.workspaces (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                admin_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
            );
        `);

        await sql.unsafe(`ALTER TABLE public.workspaces ENABLE ROW LEVEL SECURITY;`);

        await sql.unsafe(`
            DO $$ BEGIN
                CREATE POLICY "Users can access their own workspace" 
                ON public.workspaces
                FOR ALL
                USING (auth.uid() = admin_id);
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        `);

        await sql.unsafe(`
            CREATE OR REPLACE FUNCTION public.handle_new_user()
            RETURNS TRIGGER AS $$
            BEGIN
              INSERT INTO public.workspaces (name, admin_id)
              VALUES (COALESCE(NEW.raw_user_meta_data->>'name', 'Workspace of ' || split_part(NEW.email, '@', 1)), NEW.id);
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql SECURITY DEFINER;
        `);

        await sql.unsafe(`DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;`);

        await sql.unsafe(`
            CREATE TRIGGER on_auth_user_created
              AFTER INSERT ON auth.users
              FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        `);

        console.log("Migration successful");
    } catch (e) {
        console.error("Migration failed", e);
    } finally {
        await sql.end();
    }
}
migrate();
